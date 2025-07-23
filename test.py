import numpy as np
import matplotlib.pyplot as plt

def f(x):
    return x**2

def df(x):
    return 2*x

x = np.linspace(-5, 5, 100)
plt.plot(x, f(x), label='f(x)=x^2')
plt.plot(x, df(x), label="f'(x)=2x")
plt.legend()
plt.grid(True)
plt.show()
