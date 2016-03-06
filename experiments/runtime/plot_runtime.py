"""
    Make a "broken" horizontal bar plot, i.e. one with gaps, of run times.
    (c) 2015 Massachusetts Institute of Technology
"""
import numpy
import pprint
import matplotlib
matplotlib.use('GTKAgg') 
import matplotlib.pyplot as plt

label_fontsize = 11
labels = ['Disk Reset', 
#                      'Power On',
                    'OS Boot',
                    'OS Stabilize',
                    'Key Presses',
                    'Mem. (Clean)',
                    'Compress (Clean)',
#                     'Start Capture',
                    'Buttons (Clean)',
                    'Run Binary',
                    'Mem. (Interim)',
                    'Screenshot (Interim)',
                    'Buttons (Click)',
                    'Extra Sleep',
                    'Mem. (Dirty)',
                    'Screenshot (Final)',
                    'Compress (Dirty)',
                    'Shutdown',
                    'Store Results',
          'wtf',
          'wtf',
          'wtf',
          'wtf']

mal_executed_index = 7

flip_text = [6]

def normalize_tuples(tuples):

    start = tuples[0][0]

    rtn_list = []
    for tuple in tuples:
        start_x = tuple[0]-start
        x_len = tuple[1]-tuple[0]
        rtn_list.append((start_x, x_len))

    return rtn_list

# Get our virtual data
virtual_tuples = [(1439831168.838292, 1439831169.377921),
                  (1439831169.377968, 1439831190.231804),
                  (1439831190.231869, 1439831250.232374),
                  (1439831250.236563, 1439831287.317039),
                  (1439831287.317097, 1439831309.774347),
                  (1439831310.612543, 1439831402.00221), # Updated manually
                  (1439831311.01773, 1439831319.4211), (1439831319.929066, 1439831379.980296), (1439831379.98037, 1439831403.835613), (1439831403.835616, 1439831404.160049), (1439831404.160206, 1439831412.36363), (1439831412.367247, 1439831499.982088), (1439831499.98215, 1439831522.069226), (1439831522.069228, 1439831522.378756), (1439831522.378882, 1439831622.912597), (1439831622.912614, 1439831628.073827), (1439831628.108982, 1439831661.06076)]

virtual_tuples = normalize_tuples(virtual_tuples)
pprint.pprint(virtual_tuples)

# Get our physical data
physical_tuples = [(1439830680.396736, 1439831070.997367),
                   (1439831070.997433, 1439831114.95812),
                   (1439831114.958218, 1439831175.002975),
                   (1439831175.007641, 1439831216.18251),
                   (1439831216.182679, 1439831305.710553),
                   (1439831306.717004, 1439831454.234577), # Updated manually
                   (1439831307.13812, 1439831317.108357),
                   (1439831318.016684, 1439831378.074144),
                   (1439831378.074319, 1439831455.997746),
                   (1439831455.997755, 1439831460.148652),
                   (1439831460.148693, 1439831475.965947),
                   (1439831475.972392, 1439831498.053105),
                   (1439831498.053454, 1439831589.70029),
                   (1439831589.700302, 1439831594.548414),
                   (1439831594.548729, 1439831744.423983),
                   (1439831744.424003, 1439831772.876672),
                   (1439831773.100489, 1439831795.210495)]

physical_tuples = normalize_tuples(physical_tuples)
pprint.pprint(physical_tuples)
# physical_tuples = virtual_tuples

fig, (ax1, ax2) = plt.subplots(2)

y_val = len(virtual_tuples)

for idx in range(len(virtual_tuples)):
    ax1.broken_barh([ physical_tuples[idx] ] , (y_val, 1), facecolors='grey')
    ax2.broken_barh([ virtual_tuples[idx] ] , (y_val, 1), facecolors='grey')

    print virtual_tuples[idx]

    if idx == mal_executed_index:
        ax1.annotate('Binary Executed', (physical_tuples[idx][0], y_val+.5),
            xytext=(physical_tuples[idx][0]-500, y_val-2),
            arrowprops=dict(facecolor='black',
                            arrowstyle="->"),
            fontsize=label_fontsize)
        ax2.annotate('Binary Executed', (virtual_tuples[idx][0], y_val+.5),
            xytext=(virtual_tuples[idx][0]-125, y_val-2),
            arrowprops=dict(facecolor='black',
                            arrowstyle="->"),
            fontsize=label_fontsize)
    elif idx in flip_text:
        annotate_x = physical_tuples[idx][0]
        ax1.annotate(labels[idx], (annotate_x, y_val+.5),
                xytext=(annotate_x-300, y_val+.5),
                arrowprops=dict(facecolor='black',
                                arrowstyle="->"),
                fontsize=label_fontsize)

        annotate_x = virtual_tuples[idx][0]
        ax2.annotate(labels[idx], (annotate_x, y_val+.5),
                xytext=(annotate_x-125, y_val+1),
                arrowprops=dict(facecolor='black',
                                arrowstyle="->"),
                fontsize=label_fontsize)
    else:
        annotate_x = physical_tuples[idx][1] + physical_tuples[idx][0] 
        ax1.annotate(labels[idx], (annotate_x, y_val+.5),
                xytext=(annotate_x+20, y_val+1),
                arrowprops=dict(facecolor='black',
                                arrowstyle="->"),
                fontsize=label_fontsize)
        
        annotate_x = virtual_tuples[idx][1] + virtual_tuples[idx][0] 
        ax2.annotate(labels[idx], (annotate_x, y_val+.5),
                xytext=(annotate_x+20, y_val+1),
                arrowprops=dict(facecolor='black',
                                arrowstyle="->"),
                fontsize=label_fontsize)
    
    y_val -= 1
    idx += 1
    
# ax1.set_xlabel('Seconds Elapsed')
ax1.set_ylabel('Physical Analysis', fontsize=20)
ax2.set_ylabel('Virtual Analysis', fontsize=20)

max_x_virt = virtual_tuples[-1][0]+virtual_tuples[-1][1]
max_x_phy = physical_tuples[-1][0]+physical_tuples[-1][1]


ax1.set_ylim([1,len(virtual_tuples)+1])
ax2.set_ylim([1,len(virtual_tuples)+1])

ax2.set_xlabel('Time Elapsed (Minutes)', fontsize=20)

yticks = numpy.arange(len(physical_tuples))+1.5

# Remove top and right border
ax1.spines['right'].set_visible(False)
ax1.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['top'].set_visible(False)

# ax1.set_yticks(yticks)
# ax1.set_yticklabels(['']*len(virtual_tuples))
# 
# 
# ax2.set_yticks(yticks)
# ax2.set_yticklabels(['']*len(virtual_tuples))

ax1.set_yticks([])
ax2.set_yticks([])

# labels_reversed = []
# for x in reversed(labels):
#     labels_reversed.append(x)
# ax2.set_yticklabels([''] + labels_reversed)
ax2.grid(True)
ax1.grid(True)

ax1.set_xticks(range(0,int(max_x_phy*1.2),120))
ax1.set_xticklabels(range(0,200,2))


ax2.set_xticks(range(0,int(max_x_virt*1.2),60))
ax2.set_xticklabels(range(0,200,1))

ax1.set_xlim([0,max_x_phy*1.2])
ax2.set_xlim([0,max_x_virt*1.2])


for tick in ax1.xaxis.get_major_ticks():
    tick.label.set_fontsize(15)
for tick in ax1.yaxis.get_major_ticks():
    tick.label.set_fontsize(15)

for tick in ax2.xaxis.get_major_ticks():
    tick.label.set_fontsize(15)
for tick in ax2.yaxis.get_major_ticks():
    tick.label.set_fontsize(15)    
    

# ax.annotate('race interrupted', (61, 25),
#             xytext=(0.8, 0.9), textcoords='axes fraction',
#             arrowprops=dict(facecolor='black', shrink=0.05),
#             fontsize=16,
#             horizontalalignment='right', verticalalignment='top')

plt.tight_layout()
plt.savefig("runtime.eps", format='eps', dpi=1000)
# plt.show()