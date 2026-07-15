/*********************************************************************
 This is an example for our nRF52 based Bluefruit LE modules
 Pick one up today in the adafruit shop!a
 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!
 MIT license, check LICENSE for more information
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/

/* 
 *  Connect to One and Two Axis Eval Kit from Bend Labs
 *  By: Colton Ottley @ Bend Labs
 *  Date: May 5th, 2020
 *  
 *  This sketch configures an NRF52 based Arduino development board
 *  to operate as the client role to communicate with a Bend Labs
 *  One and Two Axis Eval Kit. Implements most of the functionality
 *  found in the Bend Labs Sensor Demo Android App.
 *  
 *  Tested Board: Adafruit Feather NRF52840
 *  Should work with: Adafruit Feather NRF52832 or similar 
 *  NRF52 Based Bluefruit Board
 *  
 *  Tested With Sparkfun Pro nRF52840 Mini it works but you may have to 
 *  change lines 99 & 100 in variant.h to:
 *  #define PIN_SERIAL1_RX       (15)
 *  #define PIN_SERIAL1_TX       (17)
 *  
 *  Sketch connects to first Eval Kit found and then determines
 *  if the sensor is a one or two axis sensor. Enables stretch 
 *  measurements if the sensor type is a one axis. Automatically 
 *  enables notifications on the angle measurement service and then 
 *  prints out new data received. 
 *  
 *  Uses received characters from the COM/Serial Port to trigger 
 *  calibration steps. 
 *  
 */

#include <bluefruit.h>
#include <Servo.h>

Servo myservo;  // create servo object to control a servo
// twelve servo objects can be created on most boards

int pos = 0;    // variable to store the servo position

BLEClientService        angms(0x1820);    // Angle Measurement Service
BLEClientCharacteristic angmc(0x2a70);    // Angle Measurement Characteristic

volatile bool newData = false;            // Notification callback sets true when new packet received
static float sample[] = {0.0f, 0.0f};     // Samples received through notification callback stored here

const char one_axis_model[] = "ADS_ONE_AXIS";     // Model Number String for Eval Kit when attached to One Axis
const char two_axis_model[] = "ADS_TWO_AXIS";     // Model Number String for Eval Kit when attached to Two Axis

typedef enum {
  ADS_ONE_AXIS = 0,
  ADS_TWO_AXIS, 
  ADS_UNKNOWN 
} ads_type_t;

ads_type_t adsType = ADS_UNKNOWN;         // Holds sensor type, updated in connect_callback based on DIS model string

BLEClientDis bledis;    // DIS (Device Information Service) helper class instance


void setup()
{
  myservo.attach(A2);  // attaches the servo on pin 9 to the servo object

  ///////
  Serial.begin(115200);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb

  Serial.println("Bluefruit52 Central ADS Eval Kit Example");
  Serial.println("--------------------------------------\n");

  // Initialize Bluefruit with maximum connections as Peripheral = 0, Central = 1
  // SRAM usage required by SoftDevice will increase dramatically with number of connections
  Bluefruit.begin(0, 1);

  Bluefruit.setName("Bluefruit52 Central");
  
  // Initialize Angle Measurement Service client
  angms.begin();

  // set up callback for receiving measurement
  angmc.setNotifyCallback(ams_notify_callback);
  angmc.begin();

  // Initialize the Device Information Service client
  bledis.begin();

  // Increase Blink rate to different from PrPh advertising mode
  Bluefruit.setConnLedInterval(250);

  // Callbacks for Central
  Bluefruit.Central.setDisconnectCallback(disconnect_callback);
  Bluefruit.Central.setConnectCallback(connect_callback);

  /* Start Central Scanning
   * - Enable auto scan if disconnected
   * - Interval = 100 ms, window = 80 ms
   * - Don't use active scan
   * - Filter only accept HRM service
   * - Start(timeout) with timeout = 0 will scan forever (until connected)
   */
  Bluefruit.Scanner.setRxCallback(scan_callback);
  Bluefruit.Scanner.restartOnDisconnect(true);
  Bluefruit.Scanner.setInterval(160, 80); // in unit of 0.625 ms
  Bluefruit.Scanner.filterUuid(angms.uuid);
  Bluefruit.Scanner.useActiveScan(false);
  Bluefruit.Scanner.start(0);                   // // 0 = Don't stop scanning after n seconds
}

void loop()
{
  // New data received through ams_notify_callback
  if(newData)
  {
    char s[30];
    int ss;
    int ss2;

    // Print this way to keep time in task (freertos) short.
    //sprintf(s, "%0.1f,%0.1f\r\n", sample[0], sample[1]);
    sprintf(s, "%0.0f", sample[0]);
    ss=int(sample[0]);

    ss2=(int)((ss+250)/250*90);

    //LOOP是循环，在这个里面判断数据，然后控制舵机。
    myservo.write(ss2); ////0-180
    delay(10);    
    Serial.print(ss);
    Serial.print("\r\n");

    newData = false;
  }

  // Look for data available on Serial port
  if(Serial.available())
  {
    char key = Serial.read();  // Read rx'd key
    parse_calibration(key);    // Parses key and sends to Eval Kit. Refer to function comments
  }
}

/**
 * Callback invoked when scanner pick up an advertising data
 * @param report Structural advertising data
 */
void scan_callback(ble_gap_evt_adv_report_t* report)
{
  // Since we configure the scanner with filterUuid()
  // Scan callback only invoked for device with hrm service advertised
  // Connect to device with AMS service in advertising
  Bluefruit.Central.connect(report);
}

/**
 * Callback invoked when an connection is established
 * @param conn_handle
 */
void connect_callback(uint16_t conn_handle)
{
  Serial.println("Connected");
  Serial.print("Discovering Angle Measurement Service ... ");

  // If AMS is not found, disconnect and return
  if ( !angms.discover(conn_handle) )
  {
    Serial.println("Found NONE");

    // disconnect since we couldn't find HRM service
    Bluefruit.disconnect(conn_handle);

    return;
  }

  // Once AMS service is found, we continue to discover its characteristic
  Serial.println("Found it");
  
  Serial.print("Discovering Measurement characteristic ... ");
  if ( !angmc.discover() )
  {
    // Measurement chr is mandatory, if it is not found (valid), then disconnect
    Serial.println("not found !!!");  
    Serial.println("Measurement characteristic is mandatory but not found");
    Bluefruit.disconnect(conn_handle);
    return;
  }
  Serial.println("Found it");

  if( bledis.discover(conn_handle) )
  {
    // Found device information service
    Serial.println("Found device information service");

    // Get the Model, determines if it's one axis or two axis sensor
    char s[30];
    uint16_t len = bledis.getModel(s, 30);
    s[12] = '\0'; // put null character at end of model string

    // Compare model string to see if it's one axis or two axis
    if(strcmp(s, one_axis_model) == 0)
    {
      adsType = ADS_ONE_AXIS;
      Serial.println("One Axis Sensor Found..");

      // Enable stretch measurements
      uint8_t enableStretch[] = {0x01, 0x80};  
      angmc.write(enableStretch, 2);
    }
    else if(strcmp(s, two_axis_model) == 0)
    {
      adsType = ADS_TWO_AXIS;
      Serial.println("Two Axis Sensor Found..");
    }
    else
    {
      adsType = ADS_UNKNOWN;
      Serial.println("Unknown Sensor Model..");
    }
  }

  // Reaching here means we are ready to go, let's enable notification on measurement chr
  if ( angmc.enableNotify() )
  {
    Serial.println("Ready to receive AMS Measurement value");
  }else
  {
    Serial.println("Couldn't enable notify for AMS Measurement. ");
  }
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;

  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
}


/**
 * Hooked callback that triggered when a measurement value is sent from peripheral
 * @param chr   Pointer client characteristic that even occurred,
 *              in this example it should be hrmc
 * @param data  Pointer to received data
 * @param len   Length of received data
 */
void ams_notify_callback(BLEClientCharacteristic* chr, uint8_t* data, uint16_t len)
{
  if(len == 8)
  { 
    // Parse data packet and copy to sample
    memcpy(&sample[0], &data[0], sizeof(float));
    memcpy(&sample[1], &data[4], sizeof(float));    

    // No filter present on device for the Two Axis Fw
    if(adsType == ADS_TWO_AXIS)
    {
      // Update filters
      signal_filter(sample);
    }

    deadzone_filter(sample);

    // Set newData Flag to True, print happens in loop (freertos workaround)
    newData = true;
  }
}

/* 
 *  Second order Infinite impulse response low pass filter. Sample freqency 100 Hz.
 *  Cutoff freqency 20 Hz. 
 */
void signal_filter(float * sample)
{
    static float filter_samples[2][6];

    for(uint8_t i=0; i<2; i++)
    {
      filter_samples[i][5] = filter_samples[i][4];
      filter_samples[i][4] = filter_samples[i][3];
      filter_samples[i][3] = (float)sample[i];
      filter_samples[i][2] = filter_samples[i][1];
      filter_samples[i][1] = filter_samples[i][0];
  
      // 20 Hz cutoff frequency @ 100 Hz Sample Rate
      filter_samples[i][0] = filter_samples[i][1]*(0.36952737735124147f) - 0.19581571265583314f*filter_samples[i][2] + \
        0.20657208382614792f*(filter_samples[i][3] + 2*filter_samples[i][4] + filter_samples[i][5]);   

      sample[i] = filter_samples[i][0];
    }
}

/* 
 *  If the current sample is less that 0.5 degrees different from the previous sample
 *  the function returns the previous sample. Removes jitter from the signal. 
 */
void deadzone_filter(float * sample)
{
  static float prev_sample[2];
  float dead_zone = 0.5f;

  for(uint8_t i=0; i<2; i++)
  {
    if(fabs(sample[i]-prev_sample[i]) > dead_zone)
      prev_sample[i] = sample[i];
    else
      sample[i] = prev_sample[i];
  }
}


/*
 * Parses calibration commands received through the COM/Serial Port
 * then passes received calibration commands to the angle measurement
 * characteristic. 
 *  
 * One Axis Sensor Calibration Commands
 * Step | Key | Angle | Stretch | Description
 *  1     '0'    0°       0mm     First angle calibration step     (sample[0])
 *  2     '9'   90°       0mm     Second angle calibration step    (sample[0])
 *  3     'b'    0°       0mm     First stretch calibration step   (sample[1])
 *  4     'e'    0°      30mm     Second stretch calibration step  (sample[1])
 *  -     'c'    -         -      Restores factory calibration
 * Notes: One axis sensor angle calibration coefficients won't 
 *        update before the 0° and 90° are sent.  When the 2nd stretch
 *        step is sent a decorrelation coefficient is calculated to 
 *        decorellate bend and stretch measurements. Positions of angle
 *        and stretch shown above should be observed. Order is also 
 *        important for correct operation, Step 1 before Step 2 for just angle. 
 *        Step 3 before Step 4 for just stretch. Step 1-4 for full calibration 
 *        
 *        'c' will replace most recent calibration with the calibration 
 *        stored at factory.
 *   
 * Two Axis Sensor Calibration Commands
 * Step | Key | Ang1 | Ang2 | Description
 *  1     '0'    0°     0°    First angle calibration step (sample[0], sample[1])
 *  2     'f'   90°     0°    Second angle calibration step for first axis  (sample[0])
 *  3     'p'    0°    90°    Second angle calibration step for second axis (sample[1])
 *  -     'c'    -      -     Restores factory calibration
 * Notes: Positions of both angles shown above should be observed for
 *        each step. Order is also important for correct operation. 
 *        
 *        'c' will replace most recent calibration with the calibration 
 *        stored at factory. 
 */
 void parse_calibration(char key)
 {
    uint8_t ble_msg;

    if(adsType == ADS_ONE_AXIS)
    {
      switch(key)
      {
        case '0':
          ble_msg = 0;
          angmc.write(&ble_msg, 1);
          break;
        case '9':
          ble_msg = 1;
          angmc.write(&ble_msg, 1);
          break;
        case 'b':
          ble_msg = 4;
          angmc.write(&ble_msg, 1);
          break;
        case 'e':
          ble_msg = 5;
          angmc.write(&ble_msg, 1);
          break;
        case 'c':
          ble_msg = 3;
          angmc.write(&ble_msg, 1);
          break;
      }
    }
    else if(adsType == ADS_TWO_AXIS)
    {
      switch(key)
      {
        case '0':
          ble_msg = 0;
          angmc.write(&ble_msg, 1);
          break;
        case 'f':
          ble_msg = 1;
          angmc.write(&ble_msg, 1);
          break;
        case 'p':
          ble_msg = 2;
          angmc.write(&ble_msg, 1);
          break;
        case 'c':
          ble_msg = 3;
          angmc.write(&ble_msg, 1);
          break;
      }
    }
 }
