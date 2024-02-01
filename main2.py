#!/usr/bin/
# -*- coding:utf-8 -*-

import serial
import time
import threading
import sys
import RPi.GPIO as GPIO
import chardet


ser = serial.Serial("/dev/ttyS0", 19200)

TRUE         =  1
FALSE        =  0

# Basic response message definition
ACK_SUCCESS           = 0x00
ACK_FAIL              = 0x01
ACK_FULL              = 0x04
ACK_NO_USER           = 0x05
ACK_USR_OCCUPIED      = 0x06
ACK_FINGER_OCCUPIED   = 0x07
ACK_TIMEOUT           = 0x08
ACK_GO_OUT            = 0x0F     # The center of the fingerprint is out of alignment with sensor

# User information definition
ACK_ALL_USER          = 0x00
ACK_GUEST_USER        = 0x01
ACK_NORMAL_USER       = 0x02
ACK_MASTER_USER       = 0x03

USER_MAX_CNT          = 1000        # Maximum fingerprint number

# Command definition
CMD_HEAD              = 0xF5
CMD_TAIL              = 0xF5
CMD_ADD_1             = 0x01
CMD_ADD_2             = 0x02
CMD_ADD_3             = 0x03
CMD_MATCH             = 0x0C
CMD_DEL               = 0x04
CMD_DEL_ALL           = 0x05
CMD_USER_CNT          = 0x09
CMD_COM_LEV           = 0x28
CMD_LP_MODE           = 0x2C
CMD_TIMEOUT           = 0x2E

CMD_FINGER_DETECTED   = 0x14

ID_MAX = 500

Finger_WAKE_Pin   = 23
Finger_RST_Pin    = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(Finger_WAKE_Pin, GPIO.IN)  
GPIO.setup(Finger_RST_Pin, GPIO.OUT) 
GPIO.setup(Finger_RST_Pin, GPIO.OUT, initial=GPIO.HIGH)

PC_Command_RxBuf    = []
Finger_SleepFlag    = 0

com_level = 5
rx_buf_len = 0
#rLock = threading.RLock()


def CheckSUM(command_buf):
	global rx_buf
	checksum = 0
	for i in range (1,len(command_buf)):
		checksum ^= command_buf[i]
	command_buf.append(checksum)
	command_buf.append(CMD_TAIL)
	return command_buf

def send_command(command):
	global rec_flag
	ser.flushInput()
	ser.write(command)

	rx_buf = []
	
	while len(rx_buf) < rx_buf_len:
		rec = ser.inWaiting()
		if rec !=None:
			rx_buf += ser.read(rec)
	#print (rx_buf)
	return rx_buf


def  GetCompareLevel():
	global rx_buf_len
	rx_buf_len = 8
	command_buf = [CMD_HEAD, CMD_COM_LEV, 0, 0, 1, 0]
	command = CheckSUM(command_buf)
	#print(command)
	rx = send_command(command)
	if rx[4] == ACK_SUCCESS:
		compare_level = rx[3]
		print("The Compare Level is  %d" %compare_level)
		return ACK_SUCCESS
	else:
		print("Faild to query compare_level!")
		return ACK_FAIL


def SetCompareLevel(com_level):
	global rx_buf_len
	rx_buf_len = 8
	command_buf = [CMD_HEAD, CMD_COM_LEV, 0, com_level, 0, 0]
	command = CheckSUM(command_buf)
	#print(command)
	rx = send_command(command)
	if rx[4] == ACK_SUCCESS:
		compare_level = rx[3]
		print("The Compare Level is Channaged to %d" %compare_level)
		return ACK_SUCCESS
	else:
		print("Faild to set compare_level!")
		return ACK_FAIL


def GetUserCount():
	global rx_buf_len 
	rx_buf_len = 8
	command_buf =[CMD_HEAD, CMD_USER_CNT, 0, 0, 0, 0]
	command = CheckSUM(command_buf)
	#print(command)
	rx = send_command(command)
	if rx[4] == ACK_SUCCESS:
		finger_account = rx[2] + rx[3]
		return finger_account
	else:
		print("Faild to query the account!")
		return ACK_FAIL

def ClearAllUser():
    global g_rx_buf
    command_buf = [CMD_HEAD,CMD_DEL_ALL, 0, 0, 0, 0]
    command = CheckSUM(command_buf)
    rx = send_command(command)
    if rx[4] == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if rx[4] == ACK_SUCCESS:  
        return ACK_SUCCESS
    else:
        return ACK_FAIL


def AddUser(ID = 0, permission=1):
	global rx_buf_len 
	id = GetUserCount()
	if ID > 0 and ID <ID_MAX:
		id = ID
	if permission <1 or permission >3:
		print("Faild: Invalid permission value, it should be 1, 2 or 3!")
		return ACK_FAIL

	print("Please put your finger on the center of the ")
	command_buf =[CMD_HEAD, CMD_ADD_1, 0, id+1, permission, 0]
	command = CheckSUM(command_buf)
	rx = send_command(command)
	if rx[4] == ACK_SUCCESS:
		command_buf =[CMD_HEAD, CMD_ADD_2, 0, id+1, permission, 0]
		command = CheckSUM(command_buf)
		rx = send_command(command)
		if rx[4] == ACK_SUCCESS:
			command_buf =[CMD_HEAD, CMD_ADD_3, 0, id+1, permission, 0]
			command = CheckSUM(command_buf)
			rx = send_command(command)
			if rx[4] == ACK_SUCCESS:
				print("User %d is added to database successfully" %(id+1))
				return ACK_SUCCESS
			elif rx[4] == ACK_TIMEOUT:
				print("Failed： Timeout！")
				return ACK_TIMEOUT
			else:
				print("Failed !")
				return ACK_FAIL

		elif rx[4] == ACK_TIMEOUT:
			print("Failed： Timeout！")
			return ACK_TIMEOUT
		else:
			print("Failed !")
		return ACK_FAIL
	elif rx[4] == ACK_TIMEOUT:
		print("Failed： Timeout！")
		return ACK_TIMEOUT
	elif rx[4] == ACK_FULL:
		print("The database is full!")
		return ACK_FULL
	elif rx[4] == ACK_USR_OCCUPIED:
		print ("The User was exist, please change the id and test again!")
		return ACK_USR_OCCUPIED
	elif rx[4] == ACK_FINGER_OCCUPIED:
		print ("The fingerprint was exist, please change a finger and test again!")
		return ACK_FINGER_OCCUPIED
	else:
			print("Failed !")
			return ACK_FAIL


def VerifyUser():
	global rx_buf_len 
	print("Please put your finger on the center of the sensor")
	command_buf =[CMD_HEAD, CMD_MATCH, 0, 0, 0, 0]
	command = CheckSUM(command_buf)
	time.sleep(2)
	rx = send_command(command)
	
	if rx[4] == 1 or rx[4] == 2 or rx[4] == 3:
		ID = rx[2] + rx[3]
		permission = rx[4]
		print("The user %d is macted, permission is %d"%(ID, permission))
		return ACK_SUCCESS
	elif rx[4] == ACK_TIMEOUT:
		print("Faild: Time out !")
		return ACK_TIMEOUT
	elif rx[4] == ACK_NO_USER:
		print("Faild: There is no matched fingerprint.")
		return ACK_NO_USER
	else:
		print("Faild！")
		return ACK_FAIL
		

def Analysis_PC_Command(command):
    global Finger_SleepFlag
    
    if  command == "CMD1" and Finger_SleepFlag != 1:
        print ("Number of fingerprints already available:  %d"  % GetUserCount())
    elif command == "CMD2" and Finger_SleepFlag != 1:
        print ("Add fingerprint  (Put your finger on sensor until successfully/failed information returned) ")
        r = AddUser()
        if r == ACK_SUCCESS:
            print ("Fingerprint added successfully !")
        elif r == ACK_FAIL:
            print ("Failed: Please try to place the center of the fingerprint flat to sensor, or this fingerprint already exists !")
        elif r == ACK_FULL:
            print ("Failed: The fingerprint library is full !")           
    elif command == "CMD3" and Finger_SleepFlag != 1:
        print ("Waiting Finger......Please try to place the center of the fingerprint flat to sensor !")
        r = VerifyUser()
        if r == ACK_SUCCESS:
            print ("Matching successful !")
        elif r == ACK_NO_USER:
            print ("Failed: This fingerprint was not found in the library !")
        elif r == ACK_TIMEOUT:
            print ("Failed: Time out !")
        elif r == ACK_GO_OUT:
            print ("Failed: Please try to place the center of the fingerprint flat to sensor !")
    elif command == "CMD4" and Finger_SleepFlag != 1:
        ClearAllUser()
        print ("All fingerprints have been cleared !")
    elif command == "CMD5" and Finger_SleepFlag != 1:
        GPIO.output(Finger_RST_Pin, GPIO.LOW)
        Finger_SleepFlag = 1
        print ("Module has entered sleep mode: you can use the finger Automatic wake-up function, in this mode, only CMD6 is valid, send CMD6 to pull up the RST pin of module, so that the module exits sleep !")
    elif command == "CMD6": 
        Finger_SleepFlag = 0
        GPIO.output(Finger_RST_Pin, GPIO.HIGH)
        print ("The module is awake. All commands are valid !")
    else:
        print ("commands are invalid !")

def Auto_Verify_Finger():
    while True:    
        # If you enter the sleep mode, then open the Automatic wake-up function of the finger,
        # begin to check if the finger is pressed, and then start the module and match
        if Finger_SleepFlag == 1:     
            if GPIO.input(Finger_WAKE_Pin) == 1:   # If you press your finger  
                time.sleep(0.01)
                if GPIO.input(Finger_WAKE_Pin) == 1: 
                    GPIO.output(Finger_RST_Pin, GPIO.HIGH)   # Pull up the RST to start the module and start matching the fingers
                    time.sleep(0.25)	   # Wait for module to start
                    print ("Waiting Finger......Please try to place the center of the fingerprint flat to sensor !")
                    r = VerifyUser()
                    if r == ACK_SUCCESS:
                        print ("Matching successful !")
                    elif r == ACK_NO_USER:
                        print ("Failed: This fingerprint was not found in the library !")
                    elif r == ACK_TIMEOUT:
                        print ("Failed: Time out !")
                    elif r == ACK_GO_OUT:
                        print ("Failed: Please try to place the center of the fingerprint flat to sensor !")
                            
                    #After the matching action is completed, drag RST down to sleep
                    #and continue to wait for your fingers to press
                    GPIO.output(Finger_RST_Pin, GPIO.LOW)
        time.sleep(0.2)
    

def main():
   
    GPIO.output(Finger_RST_Pin, GPIO.LOW)
    time.sleep(0.25) 
    GPIO.output(Finger_RST_Pin, GPIO.HIGH)
    time.sleep(0.25)    # Wait for module to start
    '''
    while SetCompareLevel(5) != 5:                 
        print ("***ERROR***: Please ensure that the module power supply is 3.3V or 5V, the serial line connection is correct.")
        time.sleep(1)  
        '''
    print ("***************************** WaveShare Capacitive Fingerprint Reader Test *****************************")
    print ("Compare Level:  5    (can be set to 0-9, the bigger, the stricter)")
    print ("Number of fingerprints already available:  %d "  % GetUserCount())
    print (" send commands to operate the module: ")
    print ("  CMD1 : Query the number of existing fingerprints")
    print ("  CMD2 : Registered fingerprint  (Put your finger on the sensor until successfully/failed information returned) ")
    print ("  CMD3 : Fingerprint matching  (Send the command, put your finger on sensor) ")
    print ("  CMD4 : Clear fingerprints ")
    print ("  CMD5 : Switch to sleep mode, you can use the finger Automatic wake-up function (In this state, only CMD6 is valid. When a finger is placed on the sensor,the module is awakened and the finger is matched, without sending commands to match each time. The CMD6 can be used to wake up) ")
    print ("  CMD6 : Wake up and make all commands valid ")
    print ("***************************** WaveShare Capacitive Fingerprint Reader Test ***************************** ")

    t = threading.Thread(target=Auto_Verify_Finger)
    t.setDaemon(True)
    t.start()
    
    while  True:     
        str = input("Please input command (CMD1-CMD6):")
        Analysis_PC_Command(str)
		
if __name__ == '__main__':
        try:
            main()
        except KeyboardInterrupt:
            if ser != None:
                ser.close()               
            GPIO.cleanup()
            print("\n\n Test finished ! \n") 
            sys.exit()