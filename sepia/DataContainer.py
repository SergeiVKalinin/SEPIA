import numpy as np


class DataContainer(object):
    """
    DataContainer serves to contain all data structures for a single data source (simulation or observation data).

    :var numpy.ndarray/NoneType x: x values, controllable inputs/experimental variables, shape (n, p)
    :var numpy.ndarray/NoneType y: y values, shape (n, ell)
    :var numpy.ndarray/NoneType t: t values, non-controllable inputs, shape (n, q)
    :var numpy.ndarray/NoneType y_ind: indices for multivariate y outputs, shape (ell, )
    :var numpy.ndarray/list/NoneType K: PCA basis, shape (pu, ell), or list of K matrices for each observation (for ragged observations)
    :var numpy.ndarray/list/NoneType D: discrepancy basis, shape (pv, ell), or list of D matrices (for ragged observations)
    :var numpy.ndarray/float/NoneType orig_y_sd: standard deviation of original simulation y values (may be scalar or array, length ell)
    :var numpy.ndarray/float/NoneType orig_y_mean: mean of original simulation y values (may be scalar or array, length ell)
    :var numpy.ndarray/NoneType y_std: standardized y values, shape (n, ell)
    :var numpy.ndarray/NoneType x_trans: x values transformed to unit hypercube, shape (n, p)
    :var numpy.ndarray/NoneType t_trans: t values transformed to unit hypercube, shape (n, q)
    :var numpy.ndarray/NoneType orig_t_min: minimum values (columnwise) of original t values
    :var numpy.ndarray/NoneType orig_t_max: maximum values (columnwise) of original t values
    :var numpy.ndarray/NoneType orig_x_min: minimum values (columnwise) of original x values
    :var numpy.ndarray/NoneType orig_x_max: maximum values (columnwise) of original x values
    :var list/NoneType xt_sep_design: list of separable design component matrices

    """

    def __init__(self, x, y, t=None, y_ind=None, xt_sep_design=None, Sigy=None):
        """
        Initialize DataContainer object.

        :param numpy.ndarray x: GP inputs (controllable/experimental conditions, would be known for both sim and obs), shape (n, p)
        :param numpy.ndarray/list y: GP outputs, shape (n, ell), or list of 1D arrays for ragged observations
        :param numpy.ndarray/NoneType t: optional GP inputs (not controllable, would be known only for sim), shape (n, q)
        :param numpy.ndarray/list/NoneType y_ind: optional y indices (needed if ell > 1) or list of 1D arrays for ragged observations
        :param list/NoneType sep_des: separable Kronecker design

        .. note:: DataContainer objects are constructed when you instantiate SepiaData and generally won't be instantiated directly.

        """
        self.x = x
        self.y = y
        self.t = t
        self.xt_sep_design = xt_sep_design
        self.y_ind = y_ind
        self.Sigy=Sigy

        if isinstance(self.y, list):
            self.y = [yel.squeeze() for yel in  self.y] # squeeze extra dims if provided
            self.y_ind = [yel.squeeze() for yel in self.y_ind]  # squeeze extra dims if provided
        # Parse mandatory inputs (x and y)
        if self.x.shape[0] != len(self.y):
            raise ValueError('Number of observations in x and y must be the same size.')
        # Optional inputs (depending on if sim_only or scalar_out)
        if self.t is not None and self.t.shape[0] != self.x.shape[0]:
            raise ValueError('Dimension 0 of x and t must be the same size.')
        if self.y[0].shape[0] > 1 and self.y_ind is None:
            raise ValueError('y_ind required when y has multivariate output.')
        if self.y_ind is not None:
            if isinstance(self.y_ind, list):
                y_shapes = np.array([ytmp.shape for ytmp in self.y])
                y_ind_shapes = np.array([ytmp.shape for ytmp in self.y_ind])
                if not np.all(y_shapes[:,0] == y_ind_shapes[:,0]):
                    raise ValueError('Dimension 1 of y must match dimension 0 of y_ind.')
            else:
                if self.y.shape[1] != self.y_ind.shape[0]:
                    raise ValueError('Dimension 1 of y must match dimension 0 of y_ind.')
        if self.xt_sep_design is not None:
            if not isinstance(self.xt_sep_design,list):
                raise ValueError('xt_sep_design must be a list of kronecker composable designs')
            if len(self.y) != np.prod([len(g) for g in self.xt_sep_design]):
                raise ValueError('Number of observations in kron-composed-x and y must be the same size.')

        def val_Sigy(mat,ell_obs):
            if mat.shape[0] != mat.shape[1]:
                raise ValueError('Sigy must be square - covariance of observed data')
            try:
                np.linalg.cholesky(mat)
            except:
                raise ValueError('Sigy seems to not be a valid covariance matrix')
            if len(self.Sigy) != ell_obs:
                raise ValueError('Sigy must be the same size as the number of observations')
        if self.Sigy is not None:
            if isinstance(self.y,list):
                if not isinstance(self.Sigy,list) or (len(self.Sigy)!=len(self.y)):
                    raise ValueError('for ragged obs Sigy must also be a list of same len')
                for ii in range(len(self.Sigy)):
                    self.Sigy[ii]=np.atleast_2d(self.Sigy[ii])
                    val_Sigy(self.Sigy[ii],self.y.shape[1])
            else:
                self.Sigy = np.atleast_2d(self.Sigy)
                val_Sigy(self.Sigy, self.y.shape[1])

        # Validation complete

        # Basis and transform stuff initialized to None
        self.K = None
        self.D = None
        self.orig_y_sd = None
        self.orig_y_mean = None
        self.y_std = None
        self.Sigy_std = None
        self.x_trans = None
        self.t_trans = None
        self.orig_t_min = None
        self.orig_t_max = None
        self.orig_x_min = None
        self.orig_x_max = None

    # These make sure x/y/t are 2D no matter what
    @property
    def x(self):
        return self.__x

    @x.setter
    def x(self, x):
        if not isinstance(x, list):
            if x.ndim == 1:
                x = x[:, None]
        else:
            for ii in range(len(x)):
                if x[ii].ndim == 1:
                    x[ii] = x[ii][:, None]
        self.__x = x

    @property
    def y(self):
        return self.__y

    @y.setter
    def y(self, y):
        if not isinstance(y, list):
            if y.ndim == 1:
                y = y[:, None]
        self.__y = y

    @property
    def t(self):
        return self.__t

    @t.setter
    def t(self, t):
        if t is not None:
            if t.ndim == 1:
                t = t[:, None]
        self.__t = t