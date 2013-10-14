#include <OneWire.h>
#define IBUTTON_ID_SIZE 8

OneWire ds(4); // One Wire for iButton on pin 4

unsigned long int time;             // the current time unit
unsigned long timeOfLastPulseCoins; // the time of the last pulse from the coin reader
unsigned long timeOfLastPulseBills; // the time of the last pulse from the bill reader
<<<<<<< HEAD
unsigned long heartBeat;            // the time of the last heart beat from the laptop to make sure the computer is still active
=======
>>>>>>> a105287c809ab453c80edc32efbbbd5880d22b9a
volatile int coinsValue;            // the amount of money from the coin reader
volatile int billsValue;            // the amount of money from the bill reader
volatile int coinsChange;           // 1 if the coin reader has had input, 0 otherwise
volatile int billsChange;           // 1 if the bill reader has had input, 0 otherwise
String result;                      // result from the iButton reader
byte ibutton_id[IBUTTON_ID_SIZE];   // data to hold the iButton ID

void setup()
{
  timeOfLastPulseCoins = millis();
  timeOfLastPulseBills = millis();
  heartBeat = millis();
  coinsChange = 0;
  coinsValue = 0;
  Serial.begin(9600);
  pinMode(9,OUTPUT);
  delay(500);
  digitalWrite(9, LOW);
  attachInterrupt(0, coinInserted, RISING);
  attachInterrupt(1, billInserted, FALLING);
  digitalWrite(3, HIGH);
}

/*
 * interupt method for when the coin reader pulses
 */
void coinInserted() {
  coinsValue++;
  coinsChange = 1;
  timeOfLastPulseCoins = millis();
}

/*
 * interupt method for when the bill reader pulses
 */
void billInserted() {
  billsValue++;
  billsChange = 1;
  timeOfLastPulseBills = millis();
}

<<<<<<< HEAD
/*
 * Sends the command to the readers to stop accepting money
 */
void inhibitReaders() {
  
}

/*
 * Sends the command to the readers to start accepting money
 */
void startReaders() {
  
}

=======
>>>>>>> a105287c809ab453c80edc32efbbbd5880d22b9a
void loop()
{
  String input = "";
  
  if (Serial.available()) { // if the computer writes to the arduino
    input = Serial.read();
    if (input == "l") { // user logged out
      inhibitReaders();
    } else if (input == "a") { // user was authenticated
      startReaders()
    } else if (input == "h") { // laptop sent heart beat
       heartBeat = millis();
    }
  }
  if (millis() - heartBeart > 1000) {
    startReaders();
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
  
  if (coinsChange == 1 && millis() - timeOfLastPulseCoins > 1000) {
    coinsChange = 0;
    Serial.print("m:" + String(coinsValue));
    coinsValue = 0;
  }
  if (billsChange == 1 && millis() - timeOfLastPulseBills > 1000) {
    billsChange = 0;
    Serial.print("m:" + String(billsValue * 100));
    billsValue = 0;
  }
  
}
