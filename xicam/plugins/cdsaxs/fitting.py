import numpy as np
from pyswarm import pso

import simulation

from pyevolve import G1DList
from pyevolve import GSimpleGA
from pyevolve import Selectors
from pyevolve import Statistics
from pyevolve import DBAdapters
import pyevolve

from random import randrange
import cPickle as pickle
import psutil
import multiprocessing
from collections import deque
from itertools import repeat
import panda as pd
import emcee
import deap.base as deap_base
from deap import creator, tools
from deap import cma as cmaes
'''


def pso(initiale_value, lower_bnds, upper_bnds):


    lower_bnds, upper_bnds = [], []
    for i in initiale_value:
        lower_bnds.append(int(i - 10))
        upper_bnds.append(int(i + 10))
    xopt, fopt = pso(self.residual, lower_bnds, upper_bnds)
    print(xopt, fopt)
    self.residual(xopt)
    print(opt.message)

def py_evol(num_param, num_generation, qxs, qzs):
    best_score = 0
    genome = G1DList.G1DList(num_param)
    genome.setParams(rangemin=0, rangemax=1000)
    genome.evaluator.set(self.residual)

    ga = GSimpleGA.GSimpleGA(genome)
    ga.selector.set(Selectors.GRouletteWheel)
    ga.setGenerations(num_generation)

    #ga.stepCallback.set(evolve_callback)
    ga.evolve()

    #print ga.bestIndividual()
    best = ga.bestIndividual()
    #print(best.genomeList, best.score)

    return best


def evolve_callback(ga_engine):
    generation = ga_engine.getCurrentGeneration()
    if generation % 10 == 0:
        print "Current generation: %d" % (generation,)
        best = ga_engine.bestIndividual()
        if best.score > best_score:
            best_score = best.score
            self.residual(best.genomeList, 'True')

            self.modelParameter = 5 + 0.02 * best.genomeList[2], 20 + 0.04 * best.genomeList[3], 70 + 0.04 * best.genomeList[4], best.score
            H, LL, Beta = 5 + 0.02 * best.genomeList[2], 20 + 0.04 * best.genomeList[3], np.asarray([70 + 0.04 * best.genomeList[4], 70 + 0.04 * best.genomeList[5], 70 + 0.04 * best.genomeList[6], 70 + 0.04 * best.genomeList[7], 70 + 0.04 * best.genomeList[8]])
            Obj = simulation.multipyramid(H, LL, Beta, 500, 500)
            Obj_plot = np.rot90(Obj, 3)


def residual(p, test = 'False', plot_mode=False):
    DW = 0.0001 * p[0]
    I0 = 0.01 * p[1]
    Bk = 0.01 * p[2]
    H = 5 + 0.02 * p[3]
    LL = 20 + 0.04 * p[4]
    Beta = []

    for i in range(4, len(p), 1):
        Beta.append(50 + 0.08 * p[i])

    Beta = np.array(Beta)

    Qxfit = __init__.SL_model1(H, LL, Beta, DW_factor=DW, I0=I0, Bk=Bk)

    Qxfit = corrections_DWI0Bk(Qxfit, DW_factor=DW, I0=I0, Bk=Bk, qxs, qzs)

    #self.Qxfit = correc_Isim(DW, I_scale, 1)

    res = 0
    res_min = 1000

    for i in range(0, len(self.Qxexp), 1):
        res += np.sqrt(sum((self.Qxfit[i] - self.Qxexp[i])**2) / sum((self.Qxexp[i])**2))

    maxres = min(maxres, res)
    return res
'''
def corrections_DWI0Bk(Is, DW_factor, I0, Bk, qxs, qzs):
    I_corr = []
    for I, qx, qz in zip(Is, qxs, qzs):
        DW_array = np.exp(-(np.asarray(qx) ** 2 + np.asarray(qz) ** 2) * DW_factor ** 2)
        I_corr.append(np.asarray(I) * DW_array * I0 + Bk)
    return I_corr


def log_error(exp_I_array, sim_I_array):
    error = np.nansum(np.abs(np.log10(exp_I_array) - np.log10(sim_I_array))) / np.count_nonzero(~np.isnan(exp_I_array))
    return error


def abs_error(exp_I_array, sim_I_array):
    error = np.nansum(np.abs(exp_I_array - sim_I_array) / np.nanmax(exp_I_array)) / np.count_nonzero(~np.isnan(exp_I_array))
    return error


def squared_error(exp_I_array, sim_I_array):
    error = np.nansum((exp_I_array - sim_I_array) ** 2 / np.nanmax(exp_I_array) ** 2) / np.count_nonzero(~np.isnan(exp_I_array))
    return error

'''
def fittingp_to_simp(self, fittingp):
    # DW, I0, Bk, H, LL, *Beta[5] = simp
    # values assume initial fittingp centered at 0 and std. dev. of 100
    multiples = np.array([0.0001, 0.01, 0.01, 0.02, 0.04, 0.04, 0.04, 0.04, 0.04, 0.04])
    simp = multiples * np.asarray(fittingp) + self.adds
    if np.any(simp[:5] < 0):
        return None
    if np.any(simp[5:] < 0) or np.any(simp[5:] > 180):
        return None
    return simp

@staticmethod
def fix_fitness_cmaes(fitness):
    """cmaes accepts the individuals with the lowest fitness, doesn't matter degree to which they are lower"""
    return fitness,

@staticmethod
def fix_fitness_mcmc(fitness):
    """
    Metropolis-Hastings criterion: acceptance probability equal to ratio between P(new)/P(old)
    where P is proportional to probability distribution we want to find
    for our case we assume that probability of our parameters being the best is proportional to a Gaussian centered at fitness=0
    where fitness can be log, abs, squared error, etc.
    emcee expects the fitness function to return ln(P(new)), P(old) is auto-calculated
    """
    c = 1e-1  # empirical factor to modify mcmc acceptance rate, makes printed fitness different than actual, higher c increases acceptance rate
    return -fitness / c
    # return -0.5 * fitness ** 2 / c ** 2

def cmaes(sigma, ngen, popsize, mu, N, restarts, verbose, tolhistfun, ftarget, restart_from_best=False):
    """Modified from deap/algorithms.py to return population_list instead of final population and use additional termination criteria

    Returns:
        population_list: list of (list of individuals (lists), length popsize), length ngen
        logbook: list of dicts, length ngen, contains stats for each generation
    """
    toolbox = deap_base.Toolbox()
    toolbox.register('evaluate', self.residual)
    # parallel = multiprocessing.cpu_count()
    # pool = multiprocessing.Pool(parallel)
    # toolbox.register('map', pool.map)
    # last_time = time.perf_counter()
    process = psutil.Process()
    print('{} CPUs in node'.format(multiprocessing.cpu_count()))
    print('pid:{}'.format(os.getpid()))
    print(psutil.virtual_memory())
    halloffame = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register('avg', lambda x: np.mean(np.asarray(x)[np.isfinite(x)]) if np.asarray(x)[np.isfinite(x)].size != 0 else None)
    stats.register('std', lambda x: np.std(np.asarray(x)[np.isfinite(x)]) if np.asarray(x)[np.isfinite(x)].size != 0 else None)
    stats.register('min', lambda x: np.min(np.asarray(x)[np.isfinite(x)]) if np.asarray(x)[np.isfinite(x)].size != 0 else None)
    stats.register('max', lambda x: np.max(np.asarray(x)[np.isfinite(x)]) if np.asarray(x)[np.isfinite(x)].size != 0 else None)
    stats.register('fin', lambda x: np.sum(np.isfinite(x)) / np.size(x))
    # stats.register('cumtime', lambda x: time.perf_counter() - last_time)
    stats.register('rss_MB', lambda x: process.memory_info().rss / 1048576)
    stats.register('vms_MB', lambda x: process.memory_info().vms / 1048576)
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])
    population_list = []
    kwargs = {'lambda_': popsize if popsize is not None else int(4 + 3 * np.log(N))}
    if mu is not None:
        kwargs['mu'] = mu
    initial_individual = [0] * N
    morestats = {}
    morestats['sigma_gen'] = []
    morestats['axis_ratio'] = []  # ratio of min and max scaling at each generation
    morestats['diagD'] = []  # scaling of each parameter at each generation (eigenvalues of covariance matrix)
    morestats['ps'] = []
    allbreak = False
    checkpoint_num = 0

    for restart in range(restarts + 1):
        if allbreak:
            break
        if restart != 0:
            kwargs['lambda_'] *= 2
            print('Doubled popsize')
            if restart_from_best:
                initial_individual = halloffame[0]
        # type of strategy: (parents, children) = (mu/mu_w, popsize), selection takes place among offspring only
        strategy = cmaes.Strategy(centroid=initial_individual, sigma=sigma, **kwargs)
        # The CMA-ES One Plus Lambda algorithm takes a initialized parent as argument
        #    parent = creator.Individual(initial_individual)
        #    parent.fitness.values = toolbox.evaluate(parent)
        #    strategy = cmaes.StrategyOnePlusLambda(parent=parent, sigma=sigma, lambda_=popsize)
        toolbox.register('generate', strategy.generate, creator.Individual)
        toolbox.register('update', strategy.update)

        last_best_fitnesses = deque(maxlen=10 + int(np.ceil(30 * N / kwargs['lambda_'])))
        cur_gen = 0
        # fewer generations when popsize is doubled (unless fixed ngen is specified)
        ngen_ = ngen if ngen is not None else int(100 + 50 * (N + 3) ** 2 / kwargs['lambda_'] ** 0.5)
        while cur_gen < ngen_:
            cur_gen += 1
            sys.stdout.flush()
            # Generate a new population
            population = toolbox.generate()
            population_list.append(population)
            # Evaluate the individuals
            fitnesses = toolbox.map(toolbox.evaluate, population)
            for ind, fit in zip(population, fitnesses):
                ind.fitness.values = fit  # tuple of length 1

            halloffame.update(population)
            # if cur_gen % 10 == 0:  # print best every 10 generations
            #     best = np.copy(halloffame[0])
            #     for i in range(len(best)):
            #         best[i] = self.scaling[i][1] * halloffame[0][i] + self.correction[i]
            #     print(*['{0}:{1:.3g}'.format(i, j) for i, j in zip(self.labels, best)], sep=', ')

            # Update the strategy with the evaluated individuals
            toolbox.update(population)

            record = stats.compile(population) if stats is not None else {}
            logbook.record(gen=cur_gen, nevals=len(population), **record)
            if verbose:
                print(logbook.stream)
            morestats['sigma_gen'].append(strategy.sigma)
            morestats['axis_ratio'].append(max(strategy.diagD) ** 2 / min(strategy.diagD) ** 2)
            morestats['diagD'].append(strategy.diagD ** 2)
            morestats['ps'].append(strategy.ps)

            last_best_fitnesses.append(record['min'])
            if (ftarget is not None) and record['min'] <= ftarget:
                print('Iteration terminated due to ftarget criterion after {} gens'.format(cur_gen))
                allbreak = True
                break
            if (tolhistfun is not None) and (len(last_best_fitnesses) == last_best_fitnesses.maxlen) and (
                            max(last_best_fitnesses) - min(last_best_fitnesses) < tolhistfun):
                print('Iteration terminated due to tolhistfun criterion after {} gens'.format(cur_gen))
                break
            if os.path.exists('break'):
                print('Iteration terminated due to user after {} gens'.format(cur_gen))
                break
            if os.path.exists('allbreak'):
                print('Iteration terminated due to user after {} gens'.format(cur_gen))
                allbreak = True
                break
            if os.path.exists('checkpoint{}'.format(checkpoint_num)):
                # saves current state of self as pickle and continues
                self.logbook, self.morestats, self.strategy = logbook, morestats, strategy

                self.minfitness_each_gen = self.logbook.select('min')
                self.best_uncorr = halloffame[0]
                self.best_fitness = self.best_uncorr.fitness.values[0]

                # simulate best individual one more time to print fitness and save sim_list
                # optionally plot sim and exp, plot trapezoids of best individual
                # self.fitness_individual(self.best_uncorr, plot_on=False, print_fitness=True)
                self.residual(self.best_uncorr)

                # make population dataframe, order of rows is first generation for all children, then second generation for all children...
                # make and print best individual series
                population_array = np.array(
                    [list(individual) for generation in population_list for individual in generation])
                fitness_array = np.array(
                    [individual.fitness.values[0] for generation in population_list for individual in generation])
                self.make_population_frame_best(population_array, fitness_array)
                print(self.best)
                filename = 'checkpoint{}.pickle'.format(checkpoint_num)
                with open(filename, 'wb') as f:
                    pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
                    print('saved to ' + os.path.join(os.getcwd(), filename))
                checkpoint_num += 1
        else:
            print('Iteration terminated due to ngen criterion after {} gens'.format(cur_gen))

    # pool.close()
    self.logbook = logbook
    self.morestats = morestats
    self.strategy = strategy

    self.minfitness_each_gen = self.logbook.select('min')
    self.best_uncorr = halloffame[0]  # np.abs(halloffame[0])
    self.best_fitness = halloffame[0].fitness.values[0]
    self.best_corr = self.fittingp_to_simp(self.best_uncorr)
    self.residual(self.best_uncorr, test='True')
    # make population dataframe, order of rows is first generation for all children, then second generation for all children...
    self.population_array = np.array([list(individual) for generation in population_list for individual in generation])
    self.population_array = self.fittingp_to_simp(population_array)
    self.fitness_array = np.array([individual.fitness.values[0] for generation in population_list for individual in generation])
    self.population_frame = pd.DataFrame(np.column_stack((population_array, fitness_array)))

def mcmc(self, N, sigma, nsteps, nwalkers, use_mh=False, parallel=True, seed=None, verbose=True):
    """Fit with emcee package's implementation of MCMC algorithm and place into instance of self
    Calls fitness_individual many times, then calls make_population_frame_best

    Attributes:
        best_uncorr: best uncorrected individual
        best_fitness: scalar
        minfitness_each_gen: length ngen
        sampler: instance of emcee.Sampler with detailed output of algorithm

    Args:
        self: instance of Run
        sigma: array or scalar, initial standard deviation for each parameter
        nsteps: number of steps
        nwalkers: number of walkers
        use_mh: True for Metropolis-Hastings proposal and ensemble sampler, False for ensemble sampler, 'MH' for Metropolis-Hastings proposal and sampler
        parallel: False for no parallel, True for cpu_count() processes, or int to specify number of processes, or 'scoop' for cluster
        plot_on: whether to plot fitness, best trapezoids and sim and exp scattering
        seed: seed for random number generator
    """

    def do_verbose(i, sampler):
        if (i % 100) == 0:
            print(i)
            if hasattr(sampler, 'acceptance_fraction'):
                print('Acceptance fraction: ' + str(np.mean(sampler.acceptance_fraction)))
            else:
                print('Acceptance fraction: ' + str(np.mean([sampler.acceptance_fraction for sampler in sampler])))
            sys.stdout.flush()
        if (i % 1000) == 0:
            process = psutil.Process()
            # print('time elapsed: {} min'.format((time.perf_counter() - last_time) / 60))
            print('rss_MB: {}'.format(process.memory_info().rss / 1048576))
            print('vms_MB: {}'.format(process.memory_info().vms / 1048576))

    def get_sampler(a):
        walker_num, N, sigma, nsteps, residual, verbose = a
        cov = np.identity(N) * sigma ** 2
        sampler = emcee.MHSampler(cov.copy(), cov.shape[0], residual, args=[False, False])
        for i, _ in enumerate(sampler.sample(np.zeros(N), None, None, iterations=nsteps)):
            if verbose and (walker_num == 0):
                do_verbose(i, sampler)
        return sampler

    c = 1e-1  # empirical factor to modify mcmc acceptance rate, makes printed fitness different than actual, higher c increases acceptance rate
    # last_time = time.perf_counter()
    print('{} CPUs in node'.format(multiprocessing.cpu_count()))
    print('pid:{}'.format(os.getpid()))
    print(psutil.virtual_memory())
    self.nsteps = nsteps
    self.nwalkers = nwalkers
    if seed is None:
        seed = randrange(2 ** 32)
    self.seed = seed
    np.random.seed(seed)
    self.fix_fitness = self.fix_fitness_mcmc

    if hasattr(sigma, '__len__'):
        self.sigma = sigma
    else:
        self.sigma = [sigma] * N

    # if parallel == 'scoop':
    #     if use_mh != 'MH':
    #         raise NotImplementedError
    #     self.parallel = multiprocessing.cpu_count()
    #     from scoop import futures
    #     map_MH = futures.map
    # elif parallel is True:
    #     self.parallel = multiprocessing.cpu_count()
    #     pool = multiprocessing.Pool(self.parallel)
    #     map_MH = pool.map

    self.parallel = 1
    map_MH = map

    if use_mh == 'MH':
        samplers = list(map_MH(get_sampler, zip(range(nwalkers), repeat(N), self.sigma, repeat(nsteps),
                                                repeat(self.residual), repeat(verbose))))
        chain = np.dstack(sampler.chain for sampler in samplers)
        s = chain.shape
        flatchain = np.transpose(chain, axes=[0, 2, 1]).reshape(s[0] * s[2], s[1])
        lnprobability = np.vstack(sampler.lnprobability for sampler in samplers)
        flatlnprobability = lnprobability.transpose().flatten()
        self.minfitness_each_gen = np.min(-lnprobability * c, axis=0)
    else:
        print('{} parameters'.format(N))
        if use_mh:
            individuals = [np.zeros(N) for _ in range(nwalkers)]
            mh_proposal = emcee.utils.MH_proposal_axisaligned(self.sigma)
            sampler = emcee.EnsembleSampler(
                nwalkers, N, self.residual, args=[False, False], threads=self.parallel)
            for i, _ in enumerate(sampler.sample(individuals, None, None, iterations=nsteps, mh_proposal=mh_proposal)):
                if verbose:
                    do_verbose(i, sampler)
        else:
            individuals = [[np.random.normal(loc=0, scale=s) for s in self.sigma] for _ in range(nwalkers)]
            sampler = emcee.EnsembleSampler(
                nwalkers, N, self.residual, args=[False, False], threads=self.parallel)
            for i, _ in enumerate(sampler.sample(individuals, None, None, iterations=nsteps)):
                if verbose:
                    do_verbose(i, sampler)
        s = sampler.chain.shape
        flatchain = np.transpose(sampler.chain, axes=[1, 0, 2]).reshape(s[0] * s[1], s[2])
        flatlnprobability = sampler.lnprobability.transpose().flatten()
        self.minfitness_each_gen = np.min(-sampler.lnprobability * c, axis=0)

    # if 'pool' in locals():
    #     pool.close()

    # flatchain has shape (nwalkers * nsteps, N)
    # flatlnprobability has shape (nwalkers * nsteps,)
    # flatchain and flatlnprobability list first step of all walkers, then second step of all walkers...

    # sampler.flatchain and sampler.flatlnprobability (made by package) list all steps of first walker, then all steps of second walker...
    # but we don't want that

    flatfitness = -flatlnprobability * c
    best_index = np.argmin(flatfitness)
    self.best_fitness = flatfitness[best_index]
    self.best_uncorr = flatchain[best_index]
    self.best_corr = self.fittingp_to_simp(self.best_uncorr)
    self.residual(self.best_uncorr, test='True')
    # can't make sampler attribute before run_mcmc, pickling error
    self.sampler = samplers if use_mh == 'MH' else sampler
    self.population_array = self.fittingp_to_simp(flatchain)
    self.population_frame = pd.DataFrame(np.column_stack((self.population_array, flatfitness)))
    gen_start = 0
    gen_stop = len(flatfitness)
    gen_step = 1
    popsize = int(self.population_frame.shape[0] / len(flatfitness))
    index = []
    for i in range(gen_start, gen_stop, gen_step):
        index.extend(list(range(i * popsize, (i + 1) * popsize)))
    resampled_frame = self.population_frame.iloc[index]
    self.stats = resampled_frame.describe()
    self.stats.to_csv('C:/Users/cdl/Desktop/test.csv')


'''