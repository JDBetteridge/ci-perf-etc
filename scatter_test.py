import matplotlib.pyplot as plt
from pandas import DataFrame

fig, ax = plt.subplots(1, 1)
df = DataFrame([[1, 4], [2, 5], [3, 6]], columns = ['A', 'B'])
s = df.plot.scatter('A', 'B', ax=ax)
# ~ s.collections[0].set_urls(['https://www.bbc.com/news', 'https://www.google.com/', None])
ax.collections[0].set_urls(['https://www.bbc.com/news', 'https://www.google.com/', None])
fig.savefig('scatter.svg')
