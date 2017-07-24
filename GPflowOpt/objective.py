# Copyright 2017 Joachim van der Herten
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy as np
from functools import wraps
from GPflow import model


def batch_apply(fun):
    """
    Decorator which applies a function along the first dimension of a given ndarray as argument (the batch dimension)
    the most common use case is a function which is to convert a function designed to operate on an input vector, and
    to compute its response (and possibly gradient) for each row of a matrix.

    :param fun: function accepting an input vector of dimensionality d and returns a vector of dimensionality p (the
       output dimensionality, usually one) and (optionally) a gradient of size d x p. If p is 1, the extra dimension is
       not supposed to be returned.
    :return: a function wrapper which calls fun on each row of a given n x d matrix. Here n represents the batch
       dimension. the wrapper returns n x p and optionally a n x d x p matrix (again, if p is 1 the extra dimension is
       not returned)
    """
    @wraps(fun)
    def batch_wrapper(X):
        responses = (fun(x) for x in np.atleast_2d(X))
        sep = tuple(zip(*(r if isinstance(r, tuple) else (r,) for r in responses)))
        f = np.vstack(sep[0])
        if len(sep) == 1:
            return f

        # for each point, the gradient is either (d,) or (d, p) shaped.
        g_stacked = np.stack((r for r in sep[1]), axis=0)  # n x d or n x d x p
        # Get rid of last dim = 1 in case p = 1
        g = np.squeeze(g_stacked, axis=2) if len(g_stacked.shape) == 3 and g_stacked.shape[2] == 1 else g_stacked
        return f, g

    return batch_wrapper


def to_args(fun):
    """
    Decorator for calling an objective function which has each feature as seperate input parameter. The 2d input ndarray
    is split column wise and passed as arguments. Can be combined with batch apply.
    
    :param fun: function accepting d n-dimensional vectors (each representing a feature and returns a a matrix of
       dimensionality n x p and optionally a gradient of size n x d x p (or n x d if p == 1)
    :return: a function wrapper which splits a given input ndarray into its columns to call fun.
    """
    @wraps(fun)
    def args_wrapper(X):
        X = np.atleast_2d(X)
        return fun(*X.T)

    return args_wrapper


class ObjectiveWrapper(model.ObjectiveWrapper):
    def __init__(self, objective, exclude_gradient):
        super(ObjectiveWrapper, self).__init__(objective)
        self._no_gradient = exclude_gradient
        self.counter = 0

    def __call__(self, x):
        x = np.atleast_2d(x)
        f, g = super(ObjectiveWrapper, self).__call__(x)
        self.counter += x.shape[0]
        if self._no_gradient:
            return f
        return f, g

