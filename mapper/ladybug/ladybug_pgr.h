// definitions from ladybug SDK

typedef unsigned int uint32;


typedef uint32 LadybugSerialNumber;

//   This enumeration describes the possible data formats returned by the 
//   Ladybug library. 
//
typedef enum LadybugDataFormat
{
   // This format involves interleaving every image from each of the 6 
   // image sensors on a pixel by pixel basis.  Each pixel is in its raw 
   // 8bpp format. This is the only 6 image format supported by the Ladybug.
   // This format is only supported by Ladybug1.
   LADYBUG_DATAFORMAT_INTERLEAVED,

   // This format produces a single image buffer that has each sensor's image 
   // one after the other. Again, each pixel is in its raw 8bpp format.  This 
   // format is not supported by Ladybug1.
   LADYBUG_DATAFORMAT_SEQUENTIAL,

   // This format is similar to LADYBUG_DATAFORMAT_SEQUENTIAL 
   // except that the entire buffer is JPEG compressed.  This format is 
   // intended for use with cameras that have black and white sensors. It is 
   // not supported by Ladybug1.
   LADYBUG_DATAFORMAT_SEQUENTIAL_JPEG,

   // In addition to separating the images sequentially, this format separates 
   // each individual image into its 4 individual Bayer channels (Green, Red,
   // Blue and Green - not necessarily in that order). This format is not 
   // supported by Ladybug1.
   LADYBUG_DATAFORMAT_COLOR_SEP_SEQUENTIAL,

   // This format is very similar to 
   // LADYBUG_DATAFORMAT_COLOR_SEP_SEQUENTIAL except that the transmitted
   // buffer is JPEG compressed. This format is not supported by Ladybug1.
   LADYBUG_DATAFORMAT_COLOR_SEP_SEQUENTIAL_JPEG,

   // This format is similar to LADYBUG_DATAFORMAT_SEQUENTIAL. The height
   // of the image is only half of that in LADYBUG_DATAFORMAT_SEQUENTIAL
   // format. This format is only supported by Ladybug3.
   LADYBUG_DATAFORMAT_SEQUENTIAL_HALF_HEIGHT,

   // This format is similar to LADYBUG_DATAFORMAT_COLOR_SEP_SEQUENTIAL_JPEG.
   // The height of each individual Bayer channel image is only one fourth 
   // of the original Bayer channel image. This format is only supported by 
   // Ladybug3.
   LADYBUG_DATAFORMAT_COLOR_SEP_SEQUENTIAL_HALF_HEIGHT_JPEG,

   // The number of possible data formats.
   LADYBUG_NUM_DATAFORMATS,

   // Hook for "any usable video mode".
   LADYBUG_DATAFORMAT_ANY,
   
   // Unused member to force this enumeration to compile to 32 bits.
   LADYBUG_DATAFORMAT_FORCE_QUADLET = 0x7FFFFFFF,

} LadybugDataFormat;

typedef enum LadybugResolution
{
   // 128x96 pixels. Not supported.
   LADYBUG_RESOLUTION_128x96,
   // 256x192 pixels. Not supported.
   LADYBUG_RESOLUTION_256x192,
   // 512x384 pixels. Not supported.
   LADYBUG_RESOLUTION_512x384,
   // 640x480 pixels. Not supported.
   LADYBUG_RESOLUTION_640x480,
   // 1024x768 pixels. Ladybug2 camera.
   LADYBUG_RESOLUTION_1024x768,
   // 1216x1216 pixels. Not supported.
   LADYBUG_RESOLUTION_1216x1216,
   // 1616x1216 pixels. Not supported.
   LADYBUG_RESOLUTION_1616x1216,
   // 1600x1200 pixels, Not supported.
   LADYBUG_RESOLUTION_1600x1200,
   // 1616x1232 pixels. Ladybug3 camera. 
   LADYBUG_RESOLUTION_1616x1232,

   // Number of possible resolutions.
   LADYBUG_NUM_RESOLUTIONS,
   // Hook for "any usable resolution".
   LADYBUG_RESOLUTION_ANY,
   
   // Unused member to force this enumeration to compile to 32 bits.
   LADYBUG_RESOLUTION_FORCE_QUADLET = 0x7FFFFFFF,

} LadybugResolution;

typedef enum LadybugStippledFormat
{
   // Indicates a BGGR image.
   LADYBUG_BGGR,
   // Indicates a GBRG image.
   LADYBUG_GBRG,
   // Indicates a GRBG image.
   LADYBUG_GRBG,
   // Indicates an RGGB image.
   LADYBUG_RGGB,
   // Indicates the default stipple format for the camera.
   LADYBUG_DEFAULT,

   // Unused member to force this enumeration to compile to 32 bits.
   LADYBUG_STIPPLED_FORCE_QUADLET = 0x7FFFFFFF,

} LadybugStippledFormat;


// from ladybug SDK
typedef struct LadybugStreamHeadInfo
{
   // Ladybug stream file version number.
   uint32 ulLadybugStreamVersion;

   // The compressor frame rate.
   uint32 ulFrameRate;

   // Base unit serial number for the Ladybug2 camera or ealier model.
   // For the Ladybug3 camera, it is assigned the same number as serialHead.
   LadybugSerialNumber	serialBase;

   // Camera serial number.
   LadybugSerialNumber	serialHead;

   // Reserved.
   uint32 reserved[25];

   // The size of the padding data block at the end of each recorded image.
   // The padding block is added for each image so that the total size of 
   // the recorded image data is in integer multiples of the hard disk's sector
   // size.
   uint32 ulPaddingSize;

   // Data format of the image.
   LadybugDataFormat dataFormat;

   // The resolution of the image.
   LadybugResolution resolution; 

   // The Bayer pattern of the stream.
   LadybugStippledFormat stippledFormat;

   // The size of the configuration data in bytes.
   uint32 ulConfigrationDataSize;
 
   // The number of images stored in the stream file. (Not the number of the entire stream.)
   uint32 ulNumberOfImages;

   // Number of index entries of ulOffsetTable[] used in the stream file.
   uint32 ulNumberOfKeyIndex;

   // Incremental interval value for the indexes.
   uint32 ulIncrement;
   
   // Offset of the first image data.
   uint32 ulStreamDataOffset;

   // Offset of the GPS summary data block.
   uint32 ulGPSDataOffset;

   // Size in bytes of the GPS data block.
   uint32 ulGPSDataSize;

   // Reserved.
   uint32 reservedSpace[212];

   // Image offset index table.
   uint32 ulOffsetTable[ 512 ];

} LadybugStreamHeadInfo;


// header of ladybug image (0x00 - 0x10)
typedef struct LadybugImageHeader
{
  uint32 ulTimestamp;
  uint32 ulReserved;
  uint32 ulDataSize;
  uint32 ulReserved2;
} LadybugImageHeader;

// from ladybug SDK (starting from 0x10)
typedef struct LadybugImageInfo
{
   // Constant fingerprint, should be LADYBUGIMAGEINFO_STRUCT_FINGERPRINT.
   uint32 ulFingerprint;
   // Structure version number, should be 0x00000002.
   uint32 ulVersion;
   // Timestamp, in seconds, since the UNIX time epoch.
   // If it is 0, all the data in LadybugImageInfo are invalid.
   uint32 ulTimeSeconds;
   // Microsecond fraction of above second.
   uint32 ulTimeMicroSeconds;
   // Sequence number of the image.  Reset to zero when the head powers up
   //  and incremented for every image.
   uint32 ulSequenceId;
   // Horizontal refresh rate. (reserved)
   uint32 ulHRate;
   // Actual adjusted gains used by each of the 6 cameras.  Similar to the
   //  IEEE 1394 gain register.
   uint32 arulGainAdjust[ 6 ];
   // A copy of the IEEE 1394 whitebalance register.
   uint32 ulWhiteBalance;
   // This is the same as register 0x1044, described in the Point Grey Digital Camera
   //  Register Reference.
   uint32 ulBayerGain;
   // This is the same as register 0x1040, described in the Point Grey Digital Camera
   //  Register Reference.
   uint32 ulBayerMap;
   // A copy of the Brightness IEEE 1394 register.
   uint32 ulBrightness;
   // A copy of the Gamma IEEE 1394 register.
   uint32 ulGamma;
   // The serial number of the Ladybug head.
   uint32 ulSerialNum;
   // Shutter values for each sensor.  Similar to the IEEE 1394 shutter register.
   uint32 ulShutter[ 6 ];
   // GPS Latitude, < 0 = South of Equator, > 0 = North of Equator.
   // If dGPSLatitude = LADYBUG_INVALID_GPS_DATA(defined in ladybugstream.h),
   // the data is invalid
   double        dGPSLatitude;
   // GPS Longitude, < 0 = West of Prime Meridian, > 0 = East of Prime Meridian.
   // If dGPSLongitude = LADYBUG_INVALID_GPS_DATA(defined in ladybugstream.h),
   // the data is invalid
   double        dGPSLongitude;
   // GPS Antenna Altitude above/below mean-sea-level (geoid) (in meters).
   // If dGPSAltitude = LADYBUG_INVALID_GPS_DATA(defined in ladybugstream.h),
   // the data is invalid
   double        dGPSAltitude;

} LadybugImageInfo;

