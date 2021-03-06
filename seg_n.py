# ------------------------------
# title:        seg_n.py
# author:       mofii
# date:         Jun 21, 2019
# description:  cell detector for image segmentation
# ------------------------------

import os
import sys

import cv2
import numpy as np

import matplotlib.pyplot as plt

import keras
import keras.backend as K
import tensorflow as tf

from keras.models import Sequential, Model
from keras.layers import Input, Dense, Reshape, Flatten, Dropout, Lambda, multiply
from keras.layers import BatchNormalization, Activation, Embedding, ZeroPadding2D
from keras.layers import Add, AveragePooling2D, UpSampling2D
from keras.layers.advanced_activations import LeakyReLU, ELU
from keras.layers.convolutional import UpSampling2D, Conv2D
from keras.layers.merge import concatenate
from keras.optimizers import Adam

def residual_block(X, filters, channels, stage):

    '''Residual block

    Parameters:
    X: input features
    filters (int, int): number of filters in each Conv2D layer
    channels (int): input feature channel
    stage (int): residual block index

    Implementation details:
    ELU - Conv - Dropout - ELU - Conv - Scaling
    - ELU: alpha = (default) 1.0
    - Conv: 3x3
    - Dropout: rate = 0.2
    - Scaling: factor = 0.3

    Return:
    X: ouput features
    '''

    X_shortcut = X
    F1, F2 = filters
    conv_base_name = 'res_' + str(stage) + '_branch_'
    scaling_factor = 0.3

    X = ELU()(X)
    X = Conv2D(filters=F1, kernel_size=(3, 3), strides=(1, 1), padding='same', name=conv_base_name+'2_a')(X)
    X = Dropout(rate=0.2)(X)
    X = ELU()(X)
    X = Conv2D(filters=F2, kernel_size=(3, 3), strides=(1, 1), padding='same', name=conv_base_name+'2_b')(X)
    X = Lambda(lambda x: x * scaling_factor)(X)

    X = Add()([X, X_shortcut])

    X = Conv2D(filters=channels, kernel_size=(1, 1))(X)

    return X

def cell_detector(input_shape=(128, 128, 3)):
    
    input_layer = Input(input_shape)

    X = Conv2D(32, kernel_size=(3, 3), strides=(1, 1), padding='same')(input_layer)
    res_out_1 = residual_block(X, filters=[32, 32], channels=32, stage=1)
    X = Conv2D(64, kernel_size=(3, 3), strides=(1, 1), padding='same')(res_out_1)

    # DownSampling block 1
    X = AveragePooling2D(pool_size=(2, 2), padding='valid')(X)
    res_out_2 = residual_block(X, [64, 64], 64, 2)
    X = Conv2D(128, kernel_size=(3, 3), strides=(1, 1), padding='same')(res_out_2)

    # DownSampling block 2
    X = AveragePooling2D(pool_size=(2, 2), padding='valid')(X)
    res_out_3 = residual_block(X, [128, 128], 128, 3)
    X = Conv2D(256, kernel_size=(3, 3), strides=(1, 1), padding='same')(res_out_3)

    # DownSampling block 3
    X = AveragePooling2D(pool_size=(2, 2), padding='valid')(X)
    res_out_4 = residual_block(X, [256, 256], 256, 4)
    
    # DownSampling block 4
    X = AveragePooling2D(pool_size=(2, 2), padding='valid')(X)
    X = residual_block(X, [256, 256], 256, 5)

    # UpSampling block 1
    X = UpSampling2D(size=(2, 2), interpolation='bilinear')(X)
    X = concatenate([res_out_4, X], axis=-1)
    X = residual_block(X, [512, 512], 256, 6)

    # UpSampling block 2
    X = UpSampling2D(size=(2, 2), interpolation='bilinear')(X)
    X = concatenate([res_out_3, X], axis=-1)
    X = residual_block(X, [384, 384], 128, 7)

    # UpSampling block 3
    X = UpSampling2D(size=(2, 2), interpolation='bilinear')(X)
    X = concatenate([res_out_2, X], axis=-1)
    X = residual_block(X, [192, 192], 64, 8)

    # UpSampling block 4
    X = UpSampling2D(size=(2, 2), interpolation='bilinear')(X)
    X = concatenate([res_out_1, X], axis=-1)
    X = residual_block(X, [96, 96], 32, 9)

    # Conv to ouput map
    X = Conv2D(filters=1, kernel_size=(3, 3), strides=(1, 1), padding='same')(X)

    # Create model
    model = Model(inputs=input_layer, outputs=X, name='CellDetector')

    return model

if __name__=='__main__':
    
    # ---------------------
    #  Test residual block 
    # ---------------------

    print('\nTesting residual block:')
    tf.reset_default_graph()
    with tf.Session() as test:
        np.random.seed(123)
        A_prev = tf.placeholder('float', [5, 128, 128, 3])
        X = np.random.randn(5, 128, 128, 3)
        A = residual_block(A_prev, filters=[3, 3], channels=3, stage=1)
        test.run(tf.global_variables_initializer())
        out = test.run([A], feed_dict={A_prev: X, K.learning_phase(): 0})
        print('out = ' + str(out[0][1][1][0]))
        print('Test complete: PASSED\n')

    # -------------------
    #  Test cell detector
    # -------------------

    print('\nTesting cell detector:')
    tf.reset_default_graph()
    with tf.Session() as test:
        np.random.seed(123)
        A_prev = tf.placeholder('float', [5, 128, 128, 3])
        X = np.random.randn(5, 128, 128, 3)
        model = cell_detector()
        A = model(A_prev)
        test.run(tf.global_variables_initializer())
        out = test.run([A], feed_dict={A_prev: X, K.learning_phase(): 0})
        print('out = ' + str(out[0][1][1][0]))
        print('Test complete: PASSED\n')

