KPL/FK

\beginlabel
PDS_VERSION_ID               = PDS3
RECORD_TYPE                  = STREAM
RECORD_BYTES                 = "N/A"
^SPICE_KERNEL                = "EARTHFIXEDITRF93.TF"
MISSION_NAME                 = "MARS EXPRESS"
SPACECRAFT_NAME              = "MARS EXPRESS"
DATA_SET_ID                  = "MEX-E/M-SPICE-6-V1.0"
KERNEL_TYPE_ID               = FK
PRODUCT_ID                   = "EARTHFIXEDITRF93.TF"
PRODUCT_CREATION_TIME        = 2008-09-12T09:53:25
PRODUCER_ID                  = JPL
MISSION_PHASE_NAME           = { "EV", "IC", "MC Phase 0", "MC Phase 1",
             "MC Phase 2", "MC Phase 3", "MC Phase 4", "MC Phase 5",
             "MC Phase 6", "MR Phase 1", "MR Phase 2", "MR Phase 3",
             "MR Phase 4", "MR Phase 5", "MR Phase 6", "MR Phase 7",
             "MR Phase 8", "ME Phase 1", "ME Phase 2", "ME Phase 3",
             "ME Phase 4", "ME Phase 5", "ME Phase 6", "ME Phase 7",
             "ME Phase 8", "ME Phase 9", "ME Phase 10", "ME Phase 11",
             "ME Phase 12", "ME Phase 13", "ME Phase 14", "ME Phase 15",
             "ME Phase 16", "ME Phase 17"
                               }
PRODUCT_VERSION_TYPE         = ACTUAL
START_TIME                   = "N/A"
STOP_TIME                    = "N/A"
SPACECRAFT_CLOCK_START_COUNT = "N/A"
SPACECRAFT_CLOCK_STOP_COUNT  = "N/A"
TARGET_NAME                  = "N/A"
INSTRUMENT_NAME              = "N/A"
NAIF_INSTRUMENT_ID           = "N/A"
SOURCE_PRODUCT_ID            = "EARTHFIXEDITRF93.TF"
NOTE                         = "See comments in the file for details"
OBJECT                       = SPICE_KERNEL
  INTERCHANGE_FORMAT         = ASCII
  KERNEL_TYPE                = FRAMES
  DESCRIPTION                = "This SPICE kernel associates the ITRF93
frame with the EARTH_FIXED reference frame alias "
END_OBJECT                   = SPICE_KERNEL
\endlabel


EARTH_FIXED/ITRF93 Frame Connection Kernel for New Norcia
============================================================

Updated:                    2004 March 22 01:04:00 PDT (NJB)

   Descriptive comments were added.

Creation date:              2003 June 24 04:22:00 PDT
Created by:                 Nat Bachman (JPL/NAIF)

This kernel associates the ITRF93 frame with the EARTH_FIXED
reference frame alias.  Loading this kernel together
with a kernel whose data are relative to the EARTH_FIXED frame
(for example, an SPK or topocentric frame kernel for tracking stations)
allows the SPICE system to treat that kernel's data as though
they were relative to the ITRF93 frame.  

This kernel normally should be loaded together with a binary PCK file 
providing earth rotation data.

For low-accuracy work, the IAU_EARTH frame may be used
rather than the ITRF93 frame.  The kernel EARTHFIXEDIAU.TF 
should be used in place of this one to associate the alias
EARTH_FIXED with the IAU_EARTH frame.  

\begindata

TKFRAME_EARTH_FIXED_RELATIVE = 'ITRF93'
TKFRAME_EARTH_FIXED_SPEC     = 'MATRIX'
TKFRAME_EARTH_FIXED_MATRIX   = ( 1   0   0
                                 0   1   0
                                 0   0   1 )
                                          
\begintext

