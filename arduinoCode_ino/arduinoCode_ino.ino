#include <OneWire.h>
#define IBUTTON_ID_SIZE 8

OneWire ds(4); // One Wire for iButton on pin 4

unsigned long int time;             // the current time unit
unsigned long timeOfLastPulseCoins; // the time of the last pulse from the coin reader
unsigned long timeOfLastPulseBills; // the time of the last pulse from the bill reader
unsigned long heartBeat;            // the time of the last heart beat from the laptop to make sure the computer is still active
volatile int coinsValue;            // the amount of money from the coin reader
volatile int billsValue;            // the amount of money from the bill reader
volatile int coinsChange;           // 1 if the coin reader has had input, 0 otherwise
volatile int billsChange;           // 1 if the bill reader has had input, 0 otherwise
String result;                      // result from the iButton reader
byte ibutton_id[IBUTTON_ID_SIZE];   // data to hold the iButton ID
volatile unsigned long highTime;    // the time of a high pulse from the coin reader
int coinReader = 2; 

void setup()
{
  timeOfLastPulseCoins = millis();
  timeOfLastPulseBills = millis();
  heartBeat = millis();
  coinsChange = 0;
  coinsValue = 0;
  Serial.begin(9600);
  pinMode(9,OUTPUT);
  pinMode(7,OUTPUT); // the pin used for the inhibiter
  delay(500);
  digitalWrite(9, LOW);
//  attachInterrupt(0, coinInserted, CHANGE);
  attachInterrupt(0, coinInserted, FALLING);
  attachInterrupt(1, billInserted, FALLING);
  digitalWrite(3, HIGH); // bill reader
}

/*
 * interupt method for when the coin reader pulses. This only gets the pulses that are less
 * than 150 milliseconds
 */
void coinInserted() {
//  if (digitalRead( coinReader ) == HIGH) {
 //   highTime = millis(); //get time of pulse going HIGH
 //  } else { 
 //   if (millis() - highTime < 150) { // if the pulse width was less than 150, so no start up pulses
      coinsValue++;
      coinsChange = 1;
      timeOfLastPulseCoins = millis();
  //  }
  //}
}

/*
 * interupt method for when the bill reader pulses
 */
void billInserted() {
  billsValue++;
  billsChange = 1;
  timeOfLastPulseBills = millis();
}

/*
 * Sends the command to the readers to stop accepting money
 */
void inhibitReaders() {
  digitalWrite(7, LOW);
}

/*
 * Sends the command to the readers to start accepting money
 */
void startReaders() {
  digitalWrite(7, HIGH);
}

void loop()
{
  char input;
  
  if (Serial.available()) { // if the computer writes to the arduino
    input = Serial.read();
    if (input == 'l') { // user logged out
      inhibitReaders();
    } else if (input == 'a') { // user was authenticated
      startReaders();
    } else if (input == 'h') { // laptop sent heart beat
       heartBeat = millis();
    }
  }

  if (millis() - heartBeat > 5000) {
    inhibitReaders();
  }
  // clears & initialzes the iButton buffer
  for (int i = 0 ; i < IBUTTON_ID_SIZE ; i++) {
    ibutton_id[i] = 0;
  }
  
  // reads the iButton ID, if present
  if (ds.search(ibutton_id)) {
    for (int i = IBUTTON_ID_SIZE - 1 ; i >= 0 ; i--) {
      if (ibutton_id[i] < 0x10)
        result += '0';
      result += String(ibutton_id[i], HEX);
    }
    Serial.print("i:" + result);
    delay(1000);
    result = "";
  } else {
    ds.reset_search();
  }
  
  if (coinsChange == 1 && millis() - timeOfLastPulseCoins > 200) {
    coinsChange = 0;
    Serial.print("m:" + String(coinsValue));
    coinsValue = 0;
  }
  if (billsChange == 1 && millis() - timeOfLastPulseBills > 500) {
    billsChange = 0;
    Serial.print("m:" + String(billsValue * 100));
    billsValue = 0;
  }
  
}
