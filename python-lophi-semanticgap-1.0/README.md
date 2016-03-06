# LOPHI Semantic Gap Library

This library contains code to translate low level data collected by the core LOPHI library's sensors into high level
semantically useful information.

Current features include:
* Raw SATA frames --> filesystem events, using The Sleuthkit
* Raw memory accesses --> memory objects and events, using Volatility
* Network pcaps --> protocol level information

To be as flexible and as OS-agnostic as possible, we use TSK and Volatility to bridge much of the semantic gap.

The examples/ directory contains example scripts of running disk/memory analysis on data streams from live machines as
well as on offline saved data.


## Dependencies
 - [pytsk3](https://github.com/py4n6/pytsk)
 - [Volatility](https://github.com/volatilityfoundation/volatility)


# Special Notes for Disk Analysis

For VMs, the LOPHI disk sensor provides in order sector level read/write operations, so bridging the semantic gap using
TSK is straightforward.  No SATA reconstruction is necessary.

However, on physical machines, the SATA protocol allows for Native Command Queuing (NCQ), which can interleave and
re-order multiple SATA transactions simultaneously (up to 32).  The LOPHI physical disk sensor just provides us the data
as is.  Therefore, we must perform SATA reconstruction in software as an extra step to obtain in order sector level
read/write operations before applying TSK.

The current physical disk sensor FPGA implementation on the ML507 uses an older Intelliprop SATA bridge implementation.
Unfortunately, it does not give an ideal "tap" point but rather a bridge where SATA frames may be flowing at the same time
from both sides.  As an Intelliprop engineer told me, roughly speaking, when processing frames from one side, they have
to suppress frames from the other side.  As a result, the bridge often reports multiple duplicate SATA frames even
though there was only one frame.

We currently address this and other issues in software.  See the SATA.README file under lophi/semanticgap/disk for
more details.


## SATA

Note: this applies to **physical disks only**.

SATA is a complex beast of a protocol because it is built upon older work.  We try to get as much coverage as possible,
including error handling, but the reconstruction code will likely be a work in progress for a while.

SATA has a feature called Native Command Queuing, which allows for multiple SATA transactions to be interleaved and
reordered.  This means that we must put the SATA frames reported by the LOPHI disk sensor back into a correctly ordered
serial stream before we can bridge the semantic gap.

For more information about NCQ, look at the SATA 3.0 Gold document.  Appendix B has examples of NCQ.

THe code in sata_reconstructor.py does the reconstruction by keeping track of the SATA state machine as it processes
SATA frames.

Three issues make the reconstruction process more difficult:
 1. Packet loss from the sensor
 2. Intelliprop SATA bridge problems
 3. SATA protocol quirks

If we detect that we lost a packet, we just flush all existing transactions and keep going.  We may have lost data, but
it's hard to know how to recover without knowing what the lost packet was.  In practice, I've noticed that our drives
often only has 2 transactions going at the same time under load even though the SATA spec allows for up to 32.
Hopefully SSDs will phase out NCQ and we won't have to deal with it anymore.

The Intelliprop SATA bridge on the ML507 is unfortunately not an ideal passive "tap" on the SATA bus.  Roughly speaking,
when processing frames from one side, they have to suppress frames from the other side.  As a result, the bridge often
reports multiple duplicate SATA frames even though there was only one frame because the suppressed frames get played
until they are processed.  It's unclear whether newer versions of the bridge on the ZC702 do better at this.

The SATA protocol is (sort of) well-documented, but doesn't really give many good examples of which frames are optional
in which situations and what happens with SATA errors and recovery.  Talking to an engineer who knows SATA well is
probably your best bet for getting an obscure question answered.  Our code handles the protocol to the best of our
understanding.

# Examples

* memory/
 - **example_screenshot.py** grabs a screenshot using Volatility
 - **example_buttons.py** finds and pushes UI buttons using Volatility

* disk/
 - **scan_disk_physical.py** creates a scan file image of a physical disk
 with an NTFS file system
 - **analyze_disk.py** translates low level disk accesses into filesystem
    events from a disk capture file and a scan file
 - **capture_disk.py** captures raw low-level data from a disk sensor

* network/
 - **pcap_reader.py** reads a pcap and creates src/dst pairs with info about
 the protocol based on recorded port number
 - **pcap_writer.py** creates a pcap from capturing network data

# Disclaimer
<p align="center">
This work was sponsored by the Department of the Air Force under Air
Force Contract #FA8721-05-C-0002.  Opinions, interpretations,
conclusions and recommendations are those of the authors and are not
necessarily endorsed by the United States Government.
<br>
© 2015 Massachusetts Institute of Technology 
</p>
