import numpy as np
from function.activation import *
from function.cost import *
from utility.trick import *

class AddLayer:
    """
    (class) AddLayer
    ----------------
    - The add layer
    """
    # Object initializer
    def __init__(self):
        pass

    # Do forward computations
    def forward(self, x, y):
        out = x + y

        return out

    # Do backward computations
    def backward(self, dout):
        dx = dout * 1
        dy = dout * 1

        return dx, dy

class MulLayer:
    """
    (class) MulLayer
    ----------------
    - The multiplication layer
    """
    # Object initializer
    def __init__(self):
        self.x = None
        self.y = None

    # Do forward computations
    def forward(self, x, y):
        self.x = x
        self.y = y
        out = x * y

        return out

    # Do backward computations
    def backward(self, dout):
        dx = dout * self.y
        dy = dout * self.x

        return dx, dy

class Sigmoid:
    """
    (class) Sigmoid
    ---------------
    - The sigmoid layer
    """
    # Object initializer
    def __init__(self):
        self.out = None

    # Do forward computations
    def forward(self, x):
        out = 1 / (1 + np.exp(-x))
        self.out = out

        return out

    # Do backward computations
    def backward(self, dout):
        dx = dout * (1.0 - self.out) * self.out

        return dx

class Relu:
    """
    (class) Relu
    ------------
    - The ReLU layer
    """
    # Object initializer
    def __init__(self):
        self.mask = None

    # Do forward computations
    def forward(self, x):
        self.mask = (x <= 0)
        out = x.copy()
        out[self.mask] = 0

        return out

    # Do backward computations
    def backward(self, dout):
        dout[self.mask] = 0
        dx = dout

        return dx

class Affine:
    """
    (class) Affine
    --------------
    - The affine layer

    Parameter
    ---------
    - W : weight
    - b : bias
    """
    # Object initializer
    def __init__(self, W, b):
        self.W = W
        self.b = b
        self.x = None
        self.original_x_shape = None
        self.dW = None
        self.db = None

    # Do forward computations
    def forward(self, x):
        self.original_x_shape = x.shape
        x = x.reshape(x.shape[0], -1)
        self.x = x
        out = np.dot(self.x, self.W) + self.b

        return out

    # Do backward computations
    def backward(self, dout):
        dx = np.dot(dout, self.W.T)
        self.dW = np.dot(self.x.T, dout)
        self.db = np.sum(dout, axis=0)
        dx = dx.reshape(*self.original_x_shape)

        return dx

class SoftmaxWithLoss:
    """
    (class) SoftmaxWithLoss
    -----------------------
    - The softmax with cross entropy error layer
    """
    # Object initializer
    def __init__(self):
        self.loss = None
        self.y = None
        self.t = None

    # Do forward computations
    def forward(self, x, t):
        self.t = t
        self.y = softmax(x)
        self.loss = cross_entropy_error(self.y, self.t)

        return self.loss

    # Do backward computations
    def backward(self, dout=1):
        batch_size = self.t.shape[0]
        if self.t.size == self.y.size:
            dx = (self.y - self.t) / batch_size
        else:
            dx = self.y.copy()
            dx[np.arange(batch_size), self.t] -= 1
            dx = dx / batch_size

        return dx

class Dropout:
    """
    (class) Dropout
    ---------------
    - The dropout regularization layer

    Parameter
    ---------
    - dropout_ratio : dropout probability (default = 0.5)
    """
    # Object initializer
    def __init__(self, dropout_ratio=0.5):
        self.dropout_ratio = dropout_ratio
        self.mask = None

    # Do forward computations
    def forward(self, x, train_flag=True):
        if train_flag:
            self.mask = np.random.rand(*x.shape) > self.dropout_ratio
            return x * self.mask
        else:
            return x * (1.0 - self.dropout_ratio)

    # Do backward computations
    def backward(self, dout=1):
        return dout * self.mask

class BatchNorm:
    """
    (class) BatchNorm
    -----------------
    - The batch normalization layer

    Parameter
    ---------
    - gamma : scale parameter
    - beta : shift parameter
    - momentum : moving average parameter (default = 0.9)
    - running_mean : moving average result of batch means (default = None)
    - running_var : moving average result of batch variances (default = None)
    """
    # Object initializer
    def __init__(self, gamma, beta, momentum=0.9, running_mean=None, running_var=None):
        self.gamma = gamma
        self.beta = beta
        self.momentum = momentum
        self.input_shape = None    # in case of convolution layer : 4d, in case of fully connected layer : 2d
        self.running_mean = running_mean
        self.running_var = running_var
        self.batch_size = None
        self.xc = None
        self.std = None
        self.dgamma = None
        self.dbeta = None

    # Do forward computations
    def forward(self, x, train_flag=True):
        self.input_shape = x.shape
        if x.ndim != 2:
            N, C, H, W = x.shape
            x = x.reshape(N, -1)

        out = self.__forward(x, train_flag)

        return out.reshape(*self.input_shape)

    # Do forward computations
    def __forward(self, x, train_flag=True):
        if self.running_mean is None:
            N, D = x.shape
            self.running_mean = np.zeros(D)
            self.running_var = np.zeros(D)

        if train_flag:
            mu = x.mean(axis=0)
            xc = x - mu
            var = np.mean(xc**2, axis=0)
            std = np.sqrt(var + 10e-7)
            xn = xc / std
            self.batch_size = x.shape[0]
            self.xc = xc
            self.xn = xn
            self.std = std
            self.running_mean = self.momentum * self.running_mean + (1.0 - self.momentum) * mu
            self.running_var = self.momentum * self.running_var + (1.0 - self.momentum) * var
        else:
            xc = x - self.running_mean
            xn = xc / ((np.sqrt(self.running_var + 10e-7)))

        out = self.gamma * xn + self.beta

        return out

    # Do backward computations
    def backward(self, dout):
        if dout.ndim != 2:
            N, C, H, W = dout.shape
            dout = dout.reshape(N - 1)

        dx = self.__backward(dout)
        dx = dx.reshape(*self.input_shape)

        return dx

    # Do backward computations
    def __backward(self, dout):
        dbeta = dout.sum(axis=0)
        dgamma = np.sum(self.xn * dout, axis=0)
        dxn = self.gamma * dout
        dxc = dxn / self.std
        dstd = -np.sum((dxn * self.xc) / (self.std * self.std), axis=0)
        dvar = 0.5 * dstd / self.std
        dxc += (2.0 / self.batch_size) * self.xc * dvar
        dmu = np.sum(dxc, axis=0)
        dx = dxc - dmu / self.batch_size
        self.dgamma = dgamma
        self.dbeta = dbeta

        return dx

class Convolution:
    """
    (class) Convolution
    -------------------
    - The convolution layer for CNN

    Parameter
    ---------
    - W : kernel
    - b : bias
    - stride : sliding interval (default = 1)
    - pad : data padding length (default = 0)
    """
    # Object initializer
    def __init__(self, W, b, stride=1, pad=0):
        self.W = W
        self.b = b
        self.stride = stride
        self.pad = pad
        self.x = None
        self.col = None
        self.col_W = None
        self.dW = None
        self.db = None

    # Do forward computations
    def forward(self, x):
        # Calculate output resolution information
        FN, C, FH, FW = self.W.shape
        N, C, H, W = x.shape
        out_h = 1 + int((H + 2 * self.pad - FH) / self.stride)
        out_w = 1 + int((W + 2 * self.pad - FW) / self.stride)
        
        # Apply the im2col
        col = im2col(x, FH, FW, self.stride, self.pad)
        col_W = self.W.reshape(FN, -1).T

        # Calculate forward computations like affine layer
        out = np.dot(col, col_W) + self.b
        out = out.reshape(N, out_h, out_w, -1).transpose(0, 3, 1, 2)
        self.x = x
        self.col = col
        self.col_W = col_W

        return out

    # Do backward computations
    def backward(self, dout):
        # Calculate output resolution information
        FN, C, FH, FW = self.W.shape
        dout = dout.transpose(0, 2, 3, 1).reshape(-1, FN)

        # Calculate gradients
        self.db = np.sum(dout, axis=0)
        self.dW = np.dot(self.col.T, dout)
        self.dW = self.dW.transpose(1, 0).reshape(FN, C, FH, FW)
        dcol = np.dot(dout, self.col_W.T)
        dx = col2im(dcol, self.x.shape, FH, FW, self.stride, self.pad)

        return dx

class Pooling:
    """
    (class) Pooling
    ---------------
    - The pooling layer for CNN

    Parameter
    ---------
    - pool_h : pooling height
    - pool_w : pooling width
    - stride : sliding interval (default = 1)
    - pad : data padding length (default = 0)
    """
    # Object initializer
    def __init__(self, pool_h, pool_w, stride=1, pad=0):
        self.pool_h = pool_h
        self.pool_w = pool_w
        self.stride = stride
        self.pad = pad
        self.x = None
        self.arg_max = None

    # Do forward computations
    def forward(self, x):
        # Calculate output resolution information
        N, C, H, W = x.shape
        out_h = int(1 + (H - self.pool_h) / self.stride)
        out_w = int(1 + (W - self.pool_w) / self.stride)
        
        # Apply the im2col
        col = im2col(x, self.pool_h, self.pool_w, self.stride, self.pad)
        col = col.reshape(-1, self.pool_h * self.pool_w)

        # Do max pooling
        arg_max = np.argmax(col, axis=1)
        out = np.max(col, axis=1)
        out = out.reshape(N, out_h, out_w, C).transpose(0, 3, 1, 2)
        self.x = x
        self.arg_max = arg_max

        return out

    # Do backward computations
    def backward(self, dout):
        # Calculate output resolution information
        dout = dout.transpose(0, 2, 3, 1)
        pool_size = self.pool_h * self.pool_w

        # Calculate gradients
        dmax = np.zeros((dout.size, pool_size))
        dmax[np.arange(self.arg_max.size), self.arg_max.flatten()] = dout.flatten()
        dmax = dmax.reshape(dout.shape + (pool_size,))
        dcol = dmax.reshape(dmax.shape[0] * dmax.shape[1] * dmax.shape[2], -1)
        dx = col2im(dcol, self.x.shape, self.pool_h, self.pool_w, self.stride, self.pad)

        return dx