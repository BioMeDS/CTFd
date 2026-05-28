from .MapeFlag import load as mape_load
from .MaxapeFlag import load as maxape_load
from .MseFlag import load as mse_load


def load(app):
    mse_load(app)
    mape_load(app)
    maxape_load(app)