KPL/FK
 
   FILE: KS_BDAO_JMS.tf
 
   This file was created by PINPOINT.
 
   PINPOINT Version 3.2.0 --- September 6, 2016
   PINPOINT RUN DATE/TIME:    2018-04-19T14:24:47
   PINPOINT DEFINITIONS FILE: KS_BDAO_JMS.txt
   PINPOINT PCK FILE:         pck00010.tpc
   PINPOINT SPK FILE:         KS_BDAO_JMS.bsp
 
   The input definitions file is appended to this
   file as a comment block.
 
 
   Body-name mapping follows:
 
\begindata
 
   NAIF_BODY_NAME                      += 'KS'
   NAIF_BODY_CODE                      += 399101
 
   NAIF_BODY_NAME                      += 'BDAO'
   NAIF_BODY_CODE                      += 399102
 
   NAIF_BODY_NAME                      += 'JMS'
   NAIF_BODY_CODE                      += 399103
 
\begintext
 
 
   Reference frame specifications follow:
 
 
   Topocentric frame KS_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame KS_TOPO is centered at the
      site KS, which has Cartesian coordinates
 
         X (km):                  0.1195487693244E+04
         Y (km):                  0.4783533495072E+04
         Z (km):                  0.4034328796031E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        75.9682171805556
         Latitude  (deg):        39.4791842315166
         Altitude   (km):         0.1272556428385E+01
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781366000000E+03
         Polar radius      (km):  6.3567519000000E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_KS_TOPO                       =  1399101
   FRAME_1399101_NAME                  =  'KS_TOPO'
   FRAME_1399101_CLASS                 =  4
   FRAME_1399101_CLASS_ID              =  1399101
   FRAME_1399101_CENTER                =  399101
 
   OBJECT_399101_FRAME                 =  'KS_TOPO'
 
   TKFRAME_1399101_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399101_SPEC                =  'ANGLES'
   TKFRAME_1399101_UNITS               =  'DEGREES'
   TKFRAME_1399101_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399101_ANGLES              =  (  -75.9682171805556,
                                             -50.5208157684834,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame BDAO_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame BDAO_TOPO is centered at the
      site BDAO, which has Cartesian coordinates
 
         X (km):                  0.1704608426592E+04
         Y (km):                 -0.4721687423060E+04
         Z (km):                 -0.3922663765387E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       -70.1495666666667
         Latitude  (deg):       -38.1913737299824
         Altitude   (km):         0.8133446137732E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781366000000E+03
         Polar radius      (km):  6.3567519000000E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_BDAO_TOPO                     =  1399102
   FRAME_1399102_NAME                  =  'BDAO_TOPO'
   FRAME_1399102_CLASS                 =  4
   FRAME_1399102_CLASS_ID              =  1399102
   FRAME_1399102_CENTER                =  399102
 
   OBJECT_399102_FRAME                 =  'BDAO_TOPO'
 
   TKFRAME_1399102_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399102_SPEC                =  'ANGLES'
   TKFRAME_1399102_UNITS               =  'DEGREES'
   TKFRAME_1399102_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399102_ANGLES              =  ( -289.8504333333333,
                                            -128.1913737299824,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame JMS_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame JMS_TOPO is centered at the
      site JMS, which has Cartesian coordinates
 
         X (km):                 -0.2872616249818E+04
         Y (km):                  0.3331367634356E+04
         Z (km):                  0.4603370819434E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       130.7709805555556
         Latitude  (deg):        46.4936236955438
         Altitude   (km):         0.2463237467080E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781366000000E+03
         Polar radius      (km):  6.3567519000000E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_JMS_TOPO                      =  1399103
   FRAME_1399103_NAME                  =  'JMS_TOPO'
   FRAME_1399103_CLASS                 =  4
   FRAME_1399103_CLASS_ID              =  1399103
   FRAME_1399103_CENTER                =  399103
 
   OBJECT_399103_FRAME                 =  'JMS_TOPO'
 
   TKFRAME_1399103_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399103_SPEC                =  'ANGLES'
   TKFRAME_1399103_UNITS               =  'DEGREES'
   TKFRAME_1399103_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399103_ANGLES              =  ( -130.7709805555556,
                                             -43.5063763044563,
                                             180.0000000000000 )
 
\begintext
 
 
Definitions file KS_BDAO_JMS.txt
--------------------------------------------------------------------------------
 
Create a bsp and a tf about KS, BDAO and JMS ground stations
 
begindata
 
         SITES         = ( 'KS',
                           'BDAO',
                           'JMS' )
 
         KS_CENTER = 399
         KS_FRAME  = 'EARTH_FIXED'
         KS_IDCODE = 399101
         KS_XYZ    = ( 1195.48769324396, 4783.53349507183, 4034.32879603126 )
         KS_UP     = 'Z'
         KS_NORTH  = 'X'
 
         BDAO_CENTER = 399
         BDAO_FRAME  = 'EARTH_FIXED'
         BDAO_IDCODE = 399102
         BDAO_XYZ    = ( 1704.60842659152, -4721.68742306020, -3922.66376538746 )
         BDAO_UP     = 'Z'
         BDAO_NORTH  = 'X'
 
         JMS_CENTER = 399
         JMS_FRAME  = 'EARTH_FIXED'
         JMS_IDCODE = 399103
         JMS_XYZ    = ( -2872.61624981849, 3331.36763435596, 4603.37081943369 )
         JMS_UP     = 'Z'
         JMS_NORTH  = 'X'
 
begintext
 
[End of definitions file]
 
