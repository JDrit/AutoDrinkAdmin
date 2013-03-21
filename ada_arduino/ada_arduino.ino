#include <OneWire.h>

#define IBUTTON_ID_SIZE 8
#define RFID_ID_SIZE 10

OneWire ds(4);  // on pin 4 

byte ibutton_id[IBUTTON_ID_SIZE];
char rfid_id[RFID_ID_SIZE];

int credits = 0;

void setup() 
{  
  Serial.begin(9600);
  Serial.println("");
}x

void loop() {
  String result;
  // Clear/Initialize ID buffers
  for (int i = 0; i < IBUTTON_ID_SIZE; i++)
  {
    ibutton_id[i] = 0;
  }
  
  for (int i = 0; i < RFID_ID_SIZE; i++)
  {
    rfid_id[i] = 0;
  }
  
  // Read iButton ID, if a OneWire device is available
  if (ds.search(ibutton_id))
  {
    for (int i = IBUTTON_ID_SIZE - 1; i >= 0; i--)
    {
      //if this part of the ID needs a leading 0, add one
      if(ibutton_id[i] < 0x10)
        result += '0';
      //record this part of the ID.
      result += String(ibutton_id[i],HEX);
    }
    //Send the ID to the computer
    Serial.print("i:" + result);
    //Don't spam the laptop with the same ID
    delay(2000);
  }
  else
  {
    ds.reset_search();
  }
}
