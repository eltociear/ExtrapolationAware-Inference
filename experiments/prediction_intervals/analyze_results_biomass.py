import pandas as pd
import numpy as np
import pickle
import os
import matplotlib.pyplot as plt
from matplotlib import colors
import matplotlib

# set runname
runname = 'RUNNAME'

# set output path
output_path = "experiments/results/biomass_analysis/"


# Set plotting parameters
width = 5.876
params = {'axes.labelsize': 8,
          'font.size': 8,
          'legend.fontsize': 8,
          'xtick.labelsize': 6,
          'ytick.labelsize': 6,
          'lines.linewidth': 0.7,
          'text.usetex': True,
          'axes.unicode_minus': True,
          'text.latex.preamble': r'\usepackage{amsfonts}'}
matplotlib.rcParams.update(params)
plt.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})


##
# Load results and data
##

# Load data
data_path = "experiments/prediction_intervals/biomass_data/"
wood_df = pd.read_csv(data_path + "wood.csv", sep=",")
leafs_df = pd.read_csv(data_path + "leafs.csv", sep=",")

yorg = leafs_df['Bfkg'].to_numpy().flatten()
Xorg = leafs_df['Sc'].to_numpy().reshape(-1, 1)

# Remove zeros in y and X
ind = (yorg == 0) | (Xorg[:, 0] == 0)
yorg = yorg[~ind]
Xorg = Xorg[~ind]

# log-transform data (so assumptions fit)
y = np.log(yorg)
X = np.log(Xorg)

# Create plot of data on both scales
fig, ax = plt.subplots(1, 2)
fig.set_size_inches(width, width*0.35)

ax[0].set_xlabel('crown area ($m^2$/plant)')
ax[0].set_ylabel('foilage dry mass (kg/plant)')
ax[1].set_xlabel('log crown area ($\\log(m^2))$')
ax[1].set_ylabel('log foilage dry mass ($\\log(\\mathrm{kg}))$')
ax[0].scatter(Xorg, yorg, s=5, alpha=0.3)
ax[1].scatter(X, y, s=5, alpha=0.3)
plt.savefig(
    'experiments/results/biomass_data.pdf',
    bbox_inches="tight")
plt.close()


# Load results
files = [f for f in os.listdir(output_path)
         if os.path.isfile(os.path.join(output_path, f))
         and runname + '_' in f]

res_list = [None] * len(files)
for i in range(len(files)):
    with open(output_path + f'biomass_{runname}_{i}.pkl', 'rb') as f:
        res_dict = pickle.load(f)
    res_list[i] = res_dict['res']


###
# Functions for randomized prediction intervals
###

# Function to compute calibration probability
def prob_randomized_PI(qmat, y, coverage):
    alpha_included = np.mean((qmat[:, 0] <= y) & (y <= qmat[:, 1]))
    alpha_excluded = np.mean((qmat[:, 0] < y) & (y < qmat[:, 1]))
    if coverage <= alpha_excluded:
        prob_si = 1
    elif coverage >= alpha_included:
        prob_si = 0
    else:
        prob_si = ((coverage - alpha_included) /
                   (alpha_excluded - alpha_included))
    return prob_si


# Function to compute coverage
def randomized_PI(qmat, prob_si, y):
    si_index = np.random.choice([False, True], len(y),
                                replace=True, p=[prob_si, 1-prob_si])
    included = (qmat[:, 0] < y) & (y < qmat[:, 1])
    boundary = (qmat[:, 0] == y) | (qmat[:, 1] == y)
    return (included | (boundary & si_index))


##
# Create Interpolation vs Extrapolation plot
##

# Process results
quantiles = [0.1, 0.9]
num_splits = len(res_list)
num_intervals = 1
coverage_train = np.zeros((num_splits, 2 * num_intervals))
coverage_test = np.zeros((num_splits, 2 * num_intervals))
for i in range(len(res_list)):
    train_ind = res_list[i]['train_ind']
    test_ind = ~res_list[i]['train_ind']
    ytrain = y[train_ind]
    ytest = y[test_ind]

    qmat = res_list[i]['qmat']
    bounds_list = res_list[i]['bounds_list']

    for k in range(num_intervals):
        k1 = 2*k
        k2 = 2*k + 1
        level = quantiles[k2] - quantiles[k1]
        BBlo = np.max(bounds_list[k1][:, :, 0], axis=1)
        BBup = np.min(bounds_list[k2][:, :, 1], axis=1)
        # regular quantile forest
        prob_si1 = prob_randomized_PI(qmat[train_ind, :], ytrain, level)
        qrf = randomized_PI(qmat, prob_si1, y)
        coverage_train[i, 2*k] = np.mean(qrf[train_ind])
        coverage_test[i, 2*k] = np.mean(qrf[test_ind])
        # xtrapolation quanitles
        prob_si2 = prob_randomized_PI(np.c_[BBlo[train_ind], BBup[train_ind]],
                                      ytrain, level)
        xtra = randomized_PI(np.c_[BBlo, BBup], prob_si2, y)
        coverage_train[i, 2*k+1] = np.mean(xtra[train_ind])
        coverage_test[i, 2*k+1] = np.mean(xtra[test_ind])


# Create plot
mm = int(num_splits/2)
fig, ax = plt.subplots(1, 2, sharey=True, constrained_layout=True)
fig.set_size_inches(0.9*width, width*0.3)
xgrid_train = np.linspace(0, 0.40, mm)
xgrid_test = np.linspace(0.6, 1, mm)
for k in range(2):
    ax[k].axhline(y=level, color='r', linestyle='dashed')
# extrapolation splits
# qrf
ax[0].scatter(xgrid_train, coverage_train[:mm, 0],
              edgecolor="tab:blue", alpha=0.75,
              marker="D", c='None')
ax[0].scatter(xgrid_test, coverage_test[:mm, 0],
              color="tab:blue", alpha=0.75,
              marker="D")
# xtra-qrf
ax[0].scatter(xgrid_train, coverage_train[:mm, 1],
              edgecolor="tab:green", alpha=0.75,
              marker="o", c='None')
ax[0].scatter(xgrid_test, coverage_test[:mm, 1],
              color="tab:green", alpha=0.75,
              marker="o")
# random splits
# qrf
ax[1].scatter(xgrid_train, coverage_train[mm:, 0],
              edgecolor="tab:blue", alpha=0.75,
              marker="D", c='None')
ax[1].scatter(xgrid_test, coverage_test[mm:, 0],
              color="tab:blue", alpha=0.75,
              marker="D")
# xtra-qrf
ax[1].scatter(xgrid_train, coverage_train[mm:, 1],
              edgecolor="tab:green", alpha=0.75,
              marker="o", c='None')
ax[1].scatter(xgrid_test, coverage_test[mm:, 1],
              color="tab:green", alpha=0.75,
              marker="o")
# adjust axes
xlabels = np.r_[np.arange(mm), np.arange(mm)]
xticks = np.r_[xgrid_train, xgrid_test]
for k in range(2):
    ax[k].set_xticks(xticks)
    ax[k].set_xticklabels(xlabels)
    ax[k].set_xlabel('split index')
    ax[k].text(0.25, -0.2+level, 'train', horizontalalignment='center')
    ax[k].text(0.75, -0.2+level, 'test', horizontalalignment='center')
ax[0].set_title('\\texttt{biomass}: extrapolating splits')
ax[1].set_title('\\texttt{biomass}: random splits')
ax[0].set_ylabel('coverage')
# create legend manually
p1 = matplotlib.lines.Line2D(
    [0], [0], label='quantile regression',
    marker='D', color="tab:blue", linestyle='')
p11 = matplotlib.lines.Line2D(
    [0], [0], label='\\texttt{qrf}',
    marker='D', mfc="white", mec="tab:blue", linestyle='')
p2 = matplotlib.lines.Line2D(
    [0], [0], label='\\texttt{xtra-qrf}',
    marker='o', color="tab:green", linestyle='')
p22 = matplotlib.lines.Line2D(
    [0], [0], label='xtrapolation',
    marker='o', mfc="white", mec="tab:green", linestyle='')
fig.legend([(p11, p1), (p22, p2)],
           ['\\texttt{qrf}', '\\texttt{xtra-qrf}'],
           handler_map={tuple:
                        matplotlib.legend_handler.HandlerTuple(ndivide=None)},
           ncols=1, bbox_to_anchor=(1.16, 0.75))
fig.set_tight_layout(True)
plt.savefig(
    'experiments/results/biomass_inter_vs_extra.pdf',
    bbox_inches="tight")
plt.close()


##
# Create Interpolation vs Extrapolation plot
##

n = X.shape[0]
num_splits = len(res_list)
qmat_xtra = np.zeros((n, 2))
qmat_regr = np.zeros((n, 2))
c_vec = np.zeros(n)
for split in range(int(num_splits/2)):
    train_ind = res_list[split]['train_ind']
    # train_ind = train_inds[split]
    c_vec[~train_ind] = split
    qmat = res_list[split]['qmat']
    bounds_list = res_list[split]['bounds_list']
    # quantiles
    b_up = np.min(bounds_list[1][:, :, 1], axis=1)
    b_lo = np.max(bounds_list[0][:, :, 0], axis=1)
    qmat_xtra[~train_ind, 0] = b_lo[~train_ind]
    qmat_xtra[~train_ind, 1] = b_up[~train_ind]
    qmat_regr[~train_ind, 0] = qmat[~train_ind, 0]
    qmat_regr[~train_ind, 1] = qmat[~train_ind, 1]


# Create plot
cmap = colors.ListedColormap(['tab:blue', 'tab:olive'])
fig, ax = plt.subplots(1, 2, sharey=True)
fig.set_size_inches(width, width*0.35)
sorting_vec = np.argsort(X[:, 0])[1:(n-1)]
ax[0].set_xscale('log')
ax[0].set_yscale('log')
ax[0].scatter(np.exp(X), np.exp(y), alpha=0.3, c=c_vec, s=5)
ax[0].plot(np.exp(X[sorting_vec, 0]), np.exp(qmat_regr[sorting_vec, 0]),
           color="black")
ax[0].plot(np.exp(X[sorting_vec, 0]), np.exp(qmat_regr[sorting_vec, 1]),
           color="black")
ax[0].set_ylabel('foliage dry mass (kg/plant)')
ax[0].set_xlabel('crown area ($m^2$/plant)')
ax[0].set_title('\\texttt{qrf}')
ax[1].set_xscale('log')
ax[1].set_yscale('log')
ax[1].scatter(np.exp(X), np.exp(y), alpha=0.3, c=c_vec, s=5)
ax[1].plot(np.exp(X[sorting_vec, 0]), np.exp(qmat_xtra[sorting_vec, 0]),
           color="black")
ax[1].plot(np.exp(X[sorting_vec, 0]), np.exp(qmat_xtra[sorting_vec, 1]),
           color="black")
ax[1].set_xlabel('crown area ($m^2$/plant)')
ax[1].set_title('\\texttt{xtra-qrf}')
fig.set_tight_layout(True)
plt.savefig(
    'experiments/results/biomass_quantile_scatterplot.pdf',
    bbox_inches="tight")
plt.close()


##
# Create coverage vs extrapolation score plot
##

n = X.shape[0]
num_splits = len(res_list)
qmat_xtra = np.zeros((n, 2))
qmat_qrf = np.zeros((n, 2))
qmat_xtra_train = np.zeros((n, 2))
qmat_qrf_train = np.zeros((n, 2))
score_xtra = np.zeros(n)
c_vec = np.zeros(n)
for split in range(int(num_splits/2)):
    train_ind = res_list[split]['train_ind']
    c_vec[~train_ind] = split
    qmat = res_list[split]['qmat']
    bounds_list = res_list[split]['bounds_list']
    # quantiles
    b_up1 = np.min(bounds_list[0][:, :, 1], axis=1)
    b_up2 = np.min(bounds_list[1][:, :, 1], axis=1)
    b_lo1 = np.max(bounds_list[0][:, :, 0], axis=1)
    b_lo2 = np.max(bounds_list[1][:, :, 0], axis=1)
    # test
    qmat_xtra[~train_ind, 0] = b_lo1[~train_ind]
    qmat_xtra[~train_ind, 1] = b_up2[~train_ind]
    qmat_qrf[~train_ind, 0] = qmat[~train_ind, 0]
    qmat_qrf[~train_ind, 1] = qmat[~train_ind, 1]
    # train
    qmat_xtra_train[train_ind, 0] = b_lo1[train_ind]
    qmat_xtra_train[train_ind, 1] = b_up2[train_ind]
    qmat_qrf_train[train_ind, 0] = qmat[train_ind, 0]
    qmat_qrf_train[train_ind, 1] = qmat[train_ind, 1]
    score_xtra[~train_ind] = ((b_up1 - b_lo1) + (b_up2 - b_lo2))[~train_ind]
    print(np.median(score_xtra[~train_ind]))


# Rolling window coverage
window_len = 100
coverage_xtra = np.ones(n)
coverage_qrf = np.ones(n)
perm = np.arange(n)
np.random.shuffle(perm)
score_sort = np.argsort(score_xtra[perm])
score_sort = np.argsort(score_xtra[perm])
for k in range(n):
    lo = np.max([int(k-window_len/2), 0])
    up = np.min([int(k+window_len/2), n])
    # test
    xtra_test = qmat_xtra[perm, :][score_sort[lo:up], :]
    qrf_test = qmat_qrf[perm, :][score_sort[lo:up], :]
    # train
    xtra_train = qmat_xtra_train[perm, :][score_sort[lo:up], :]
    qrf_train = qmat_qrf_train[perm, :][score_sort[lo:up], :]
    true_y = y[perm][score_sort[lo:up]]
    # coverage
    prob_si = prob_randomized_PI(qrf_train,
                                 true_y, level)
    coverage_qrf[k] = np.mean(randomized_PI(qrf_test, prob_si, true_y))
    prob_si = prob_randomized_PI(xtra_train,
                                 true_y, level)
    coverage_xtra[k] = np.mean(randomized_PI(xtra_test, prob_si, true_y))


fig, ax = plt.subplots(1, 1)
fig.set_size_inches(0.5*width, width*0.35)
ax.plot(coverage_xtra, color="tab:green", label='\\texttt{xtra-qrf}')
ax.plot(coverage_qrf, color="tab:blue", label='\\texttt{qrf}')
ax.axhline(0.8, linestyle='dashed', c='red')
ax.set_title('\\texttt{biomass}')
ax.set_xlabel('extrapolation score')
ax.set_ylabel('smoothed coverage')
plt.legend(ncol=1)
fig.set_tight_layout(True)
plt.savefig(
    'experiments/results/biomass_extrapolation_score.pdf',
    bbox_inches="tight")
plt.close()


# # Cummulative coverage
# coverage_xtra = np.ones(n)
# coverage_qrf = np.ones(n)
# score_sort = np.argsort(score_xtra)
# for k in range(10, n):
#     # test
#     xtra_test = qmat_xtra[score_sort[:k], :]
#     qrf_test = qmat_qrf[score_sort[:k], :]
#     # train
#     xtra_train = qmat_xtra_train[score_sort[:k], :]
#     qrf_train = qmat_qrf_train[score_sort[:k], :]
#     true_y = y[score_sort[:k]]
#     # coverage
#     prob_si = prob_randomized_PI(qrf_train,
#                                  true_y, level)
#     coverage_qrf[k] = np.mean(randomized_PI(qrf_test, prob_si, true_y))
#     prob_si = prob_randomized_PI(xtra_train,
#                                  true_y, level)
#     coverage_xtra[k] = np.mean(randomized_PI(xtra_test, prob_si, true_y))


# fig, ax = plt.subplots(1, 1)
# fig.set_size_inches(0.5*width, width*0.35)
# ax.plot(coverage_xtra, color="tab:green", label='\\texttt{xtra-qrf}')
# ax.plot(coverage_qrf, color="tab:blue", label='\\texttt{qrf}')
# ax.axhline(0.8, linestyle='dashed', c='red')
# ax.set_title('biomass data')
# ax.set_xlabel('samples sorted w.r.t. extrapolation score')
# ax.set_ylabel('smoothed coverage')
# plt.legend(ncol=1)
# fig.set_tight_layout(True)
# plt.savefig(
#     'experiments/results/biomass_extrapolation_score.pdf',
#     bbox_inches="tight")
# plt.close()