#include <OneWire.h>

#define IBUTTON_ID_SIZE 8
#define RFID_ID_SIZE 10

OneWire ds(4);  // on pin 4 

byte ibutton_id[IBUTTON_ID_SIZE];
char rfid_id[RFID_ID_SIZE];

const int coinInt = 0; 
//Attach coinInt to Interrupt Pin 0 (Digital Pin 2). Pin 3 = Interrpt Pin 1.
const int billInt = 1;

volatile int coinsValue = 0;
volatile int billsValue = 0;
//Set the coinsValue and billsValue to a Volatile float
//Volatile as this variable changes any time the Interrupt is triggered
int coinsChange = 0; //A Coin has been inserted flag
int billsChange = 0; //A bill has been inserted flag

unsigned long timeOfLastPulseCoins;
unsigned long timeOfLastPulseBills;

void setup() 
{  
  Serial.begin(9600);
  //Serial.println("");
  
  attachInterrupt(coinInt, coinInserted, RISING);
  attachInterrupt(billInt, billInserted, RISING);
//If coinInt goes HIGH (a Pulse), call the coinInserted function
//An attachInterrupt will always trigger, even if your using delays
  timeOfLastPulseCoins = millis();
  timeOfLastPulseBills = millis();
  
}

void coinInserted()    
//The function that is called every time it recieves a pulse
{
  coinsValue += 1;  
//As we set the Pulse to represent 5p or 5c we add this to the coinsValue
  coinsChange = 1;                           
//Flag that there has been a coin inserted
  
  timeOfLastPulseCoins = millis();
}

void billInserted()
{
  billsValue += 100;
  billsChange = 1;
  timeOfLastPulseBills = millis();
}  

void loop() {
  if(Serial.available())
  {
    //Serial.println(Serial.read());
  }
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
    delay(1000);
  }
  else
  {
    ds.reset_search();
  }
  
  
  if(coinsChange == 1 && millis() - timeOfLastPulseCoins > 1000)
//Check if a coin has been Inserted
  {
    coinsChange = 0;              
//unflag that a coin has been inserted
  
    Serial.print("m:" + String(coinsValue));
//    Serial.println(coinsValue);    
//Print the Value of coins inserted
    coinsValue=0;
  }
  
  if (billsChange == 1 && millis() - timeOfLastPulseBills > 1000)
  {
    billsChange = 1;
    Serial.print("m:" + String(billsValue));
    billsValue = 0;
  }
}  
