# CODE FROM XIAORAN CHEN https://github.com/aubreychen9012/AutoEncoder_AnomalyDetection

import numpy as np
import math
from pdb import set_trace as bp

def gaussian_negative_log_likelihood(x, mu, std):
    sq_x = (x - mu)**2
    #sq_std = std**2
    sq_std = np.exp(std)
    #sq_std = (tf.log(std**2+1e-10))**2
    log_x = - sq_x / (sq_std+1e-10)
    C = -0.5 * np.log(2.*math.pi*sq_std+1e-10)
    return -(C + log_x)

def l2loss(x,y):
    summed = np.reduce_sum((y - x)**2,
                           [1, 2, 3])
    #sqrt_summed = tf.sqrt(summed)
    l2_loss = summed
    return l2_loss

def l2loss_np(x,y):
    summed = (y - x)**2
    #sqrt_summed = tf.sqrt(summed + 1e-10)
    l2 = summed
    return l2

def l1loss(x,y):
    summed = np.reduce_sum(np.abs(y - x), axis=[1, 2, 3])
    #sqrt_summed = tf.sqrt(summed + 1e-10)
    l1_loss = summed
    return l1_loss

def l1loss_np(x,y):
    l1 = np.abs(y - x)
    #sqrt_summed = tf.sqrt(summed + 1e-10)
    return l1


def kl_loss_1d(z_mean,z_stddev):
    latent_loss = np.reduce_sum(
        np.square(z_mean) + np.square(z_stddev) - 2.*np.log(z_stddev) - 1, [1,2,3])
    return 0.5*latent_loss

def kl_loss_1d_1d(z_mean,z_stddev):
    latent_loss = np.reduce_sum(
        np.square(z_mean) + np.square(z_stddev) - np.log(z_stddev + 1e-10) - 1, [1])
    return latent_loss

def batch_transpose(x):
    # only for dim(x)==4
    x = np.transpose(x, perm = [0,1,3,2])
    return x

def kl_cov_gaussian(mu, A):
    n = np.shape(mu)[0]
    c = np.shape(mu)[1]
    h = np.shape(mu)[-1]
    sigma = np.matmul(batch_transpose(A), A)+np.eye(h, h, batch_shape=[n, c]) * 1e-8

    mu = batch_transpose(mu)

    mu0 = np.zeros_like(mu)
    sigma0 = np.eye(h, h, batch_shape=[n, c])
    #eps = tf.eye(h, h, batch_shape=[n, c])*1e-10

    #mu0 = [[0, 0, 0, 0]]
    #sigma0 = tf.eye(4)

    sigma_inv = np.linalg.inv(sigma0)
    _dot = np.matmul(sigma_inv, sigma)
    _dot = np.trace(_dot)

    _matmul = np.matmul(batch_transpose(mu0-mu), np.linalg.inv(sigma0))
    _matmul = np.matmul(_matmul, (mu0-mu))
    _matmul = np.reshape(_matmul, [n,c])

    _k = np.linalg.trace(sigma0)

    _log = np.log(np.linalg.det(sigma0)+1e-8)-np.log(np.linalg.det(sigma)+1e-8)

    #_log = tf.linalg.logdet(sigma0)-tf.linalg.logdet(sigma)

    kl = 0.5*(_dot + _matmul - _k + _log)
    kl = np.reduce_sum(kl, [1])
    return kl

def perceputal_loss(x, params, vgg19):
    """
    see vunet repository
    :param x:
    :param params:
    :return:
    """
    return 5.0 * vgg19.make_loss_op(x, params)

def negative_nllh(x, mu, sigma):
    #sigma = tf.minimum(sigma, np.log(np.sqrt(2.)))
    #sigma_max = tf.maximum(1e-10, sigma)
    sum_sigma = -np.reduce_sum(sigma, axis=[1,2,3])
    sum_frac = np.reduce_sum(np.square(x-mu)*(np.exp(sigma)**2/2.), axis=[1,2,3])
    llh = sum_frac + sum_sigma
    return llh

def negative_llh_var(x, mu, sigma):
    #sigma = tf.minimum(sigma, np.log(np.sqrt(2.)))
    #sigma_max = tf.maximum(1e-10, sigma)
    sum_sigma = -np.reduce_sum(sigma, axis=[1,2,3])
    sum_frac = np.reduce_sum((x-mu)**2*np.exp(sigma), axis=[1,2,3])
    llh = sum_frac + sum_sigma
    return llh

def llh(x, mu, sigma):
    #sigma_min = np.minimum(sigma, np.log(1e4))
    sum_sigma = -sigma
    sum_frac = ((x - mu)**2) * np.exp(sigma)
    llh = sum_frac + sum_sigma
    return llh

def aggregate_var_loss(mu, true_image, pred_var):
    decoder_err_mu = np.zeros_like(mu)
    for i in range(25):
        # err = (mu - true_image)**2
        err = np.abs(mu-true_image)
        decoder_err_mu += err
    decoder_err_mu = decoder_err_mu / 25.
    loss = l1loss(pred_var, decoder_err_mu)
    return loss, decoder_err_mu




