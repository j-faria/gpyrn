import numpy as np
import matplotlib
matplotlib.rcParams.update({
    "pgf.texsystem": "pdflatex",
    'font.family': 'serif',
    'text.usetex': True,
    'pgf.rcfonts': False})
import matplotlib.pylab as plt
plt.close('all')
plt.rcParams['figure.figsize'] = [7, 4]
from matplotlib.ticker import AutoMinorLocator

from gpyrn import meanfield

time = np.linspace(0, 100, 25)
y1 = 20*np.sin(2*np.pi*time / 31)
y1err = np.random.rand(25)

plt.figure()
plt.errorbar(time, y1, y1err, fmt='ob', markersize=7, label='y1')
plt.xlabel('Time (days)')
plt.ylabel('Measurements')
plt.grid(which='major', alpha=0.5)
plt.savefig('data.png', bbox_inches='tight')
plt.close('all')

from gpyrn import covfunc, meanfunc
############## 1 dataset 
gprn = meanfield.inference(1, time, y1, y1err)

nodes = [covfunc.Periodic(15, 31, 0.5)]
weight = [covfunc.SquaredExponential(1, 1)]
means = [meanfunc.Constant(0)]
jitter = [0.5]

elbo, m, v = gprn.ELBOcalc(nodes, weight, means, jitter, 
                           iterations=5000, mu='init', var='init')
print('ELBO =', elbo)


nodes = [covfunc.Periodic(15, 31, 0.5)]
weight = [covfunc.SquaredExponential(1, 100)]
means = [meanfunc.Constant(0)]
jitter = [0.5]

elbo, m, v = gprn.ELBOcalc(nodes, weight, means, jitter, 
                           iterations=5000, mu='init', var='init')
print('ELBO =', elbo)


tstar = np.linspace(time.min()-10, time.max()+10, 5000)
mean, _, _ = gprn.Prediction(nodes, weight, means, jitter, tstar, m, v)

plt.figure()
plt.errorbar(time, y1, y1err, fmt='ob', markersize=7, label='data')
plt.plot(tstar, mean[0], '--k', linewidth=2, label='predictive')
plt.xlabel('Time (days)')
plt.ylabel('Measurements')
plt.legend(loc='upper right', facecolor='white', framealpha=1, edgecolor='black')
plt.grid(which='major', alpha=0.5)
plt.savefig('dataAndPrediction.png', bbox_inches='tight')
plt.close('all')