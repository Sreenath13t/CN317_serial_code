from blazecontroller import util
import time
import subprocess
import json
import syslog
from evm import parameters as param
from evm import cn317 as motor
from tenxer_drivers import relay_switch
from tenxer_drivers import uv4l_stream as uv4l
from evm.us082uart import SerialCom 
import random
X_AXIS_WIDTH = 50
COUNTER = 0

DIR = 1
SPEED = 25

def __inform_ui(ws, lock, command, video_url, tag):
    message = {
        'cmd': command if command == 'video' else 'canvas_video',
        'output_container': ['canvas_video' if command == 'video' else command],
        'output_element': ['canvas_video' if command == 'video' else command],
        'handler': 'canvas_video',
        'units': 'ppm',
        'data': [video_url],
        'tag': tag,
        'status': False,
        'agent': 'blaze'
    }
    data = json.dumps(message).encode('utf-8')
    # print (device_constants.VIDEO_URL)
    util.ws_send(ws, lock, 'video', data)  # NewChange
    print("STREAM STARTED AT", video_url)


#new change which can stream the video mapped with label instead UUID

def _inform_ui(ws,req,lock,command,video_url,tag):
    message = None

    if command == 'video':
        message = {'cmd': command, 'output_container': ['canvas_video'], 'output_element': ['canvas_video'],'handler':'canvas_video',
                'units': 'ppm', 'data': [video_url],'tag':tag, 'status': False, 'agent': 'blaze'}
    else:
        for i in req['output_element'] :
             if i.get('label') == command :
                    command = i.get('value')
                    message = {'cmd': 'canvas_video', 'output_container': [command], 'output_element': [command],'handler':'canvas_video',
                    'units': 'ppm', 'data': [video_url],'tag':tag, 'status': False, 'agent': 'blaze'}
    if message:
        data = json.dumps(message).encode('utf-8')
        #print (device_constants.VIDEO_URL)
        util.ws_send(ws,lock,'video',data) # NewChange
        print ("STREAM STARTED AT", video_url)


def blaze_button(req,ws,lock,msg):
    if msg == "START_MOTOR":
        data = 'START_MOTOR'
        req['output_container'] = {'metadata': {"color": "FFFFFF", "background": "468500", "disable": False}}
        util.format_output(req, ws, lock, [data], len(data), [True], 'f4f9c822-e4ce-33e7-9f0c-151e31a7fe94')

        data = 'RESOLUTION TEST'
        req['output_container'] = {'metadata': {"color": "FFFFFF", "background": "19395f", "disable": True}}
        util.format_output(req, ws, lock, [data], len(data), [True], '55d185ca-194c-6c82-f1c5-af7ae4bb8818')

    elif msg == "STOP_MOTOR":
        data = 'STOP_MOTOR'
        req['output_container'] = {'metadata': {"color": "FFFFFF", "background": "FF0000", "disable": False}}
        util.format_output(req, ws, lock, [data], len(data), [True], 'start_button')

        data = 'RESOLUTION TEST ON'
        req['output_container'] = {'metadata': {"color": "FFFFFF", "background": "0000FF", "disable": False}}
        util.format_output(req, ws, lock, [data], len(data), [True], 'resolution_button')

    elif msg == "STOP_RES":
        data = 'RESOLUTION TEST OFF'
        req['output_container'] = {'metadata': {"color": "FFFFFF", "background": "FF0000", "disable": False}}
        util.format_output(req, ws, lock, [data], len(data), [True], 'resolution_button')







def __update_information_session(req, ws, lock, msg, data_clear=True):
    req['output_container'] = None
    util.format_output(req, ws, lock, [msg], len(msg), [data_clear], 'info')


### Refer Parameters file for MESSAGE_TYPE ######
def __send_notification(req, ws, lock, msg, message_type):
    error_response = {
        'cmd': 'notification',
        'data': [msg],
        "handler": None,
        "clear_data": True,
        "output_element": [],
        "output_container": {
            "metadata": {
                "type": message_type
            }
        },
        'agent': 'blaze'
    }
    data = json.dumps(error_response).encode('utf-8')
    util.ws_send(ws, lock, 'notification', data)  # NewChange


def _end_of_feature(ws, lock):
    '''
    Draws a short line to segregate each feature set
    '''
    msg = '---'
    util.send_status(ws, lock, 'reset_initial_settings', msg, False)

def __graph_metadata():
    res = {
        "metadata": {
            "y1": {
                "list_number": [0],
                "type": ["line"],
                "list_label": ["Serial Data"],
                "axis_label": {"x": "", "y": ""},
                "scale_min": {"x": 0},
                "scale_max": {"x": X_AXIS_WIDTH}
            }
        }
    }
    return res

def connect(req, ws, lock, event, shared_live_queue):
    """
    This is called from the Connect routine of UI. The no_wait is noted
    so that the graph time can start plotting considering the "connect" time
    as Zero. The default values are rewritten on the registers. 
    Args:
        ws: Websocket address
        lock: Lock for hardware access
        shared_list: List shared by other process
        queue: Memory location of the queue which contains data of live process
    Returns:
        EXIT
    """
    global SD
    if req.get("start_time") == None:
        global COUNTER
        req["start_time"] = time.time()
        req['elk_stack'] = None
        COUNTER = 0
        msg = "$> Initializing {0} - {1}".format(param.EVM_CODE, param.EVM_NAME)
        util.send_status(ws, lock, 'connect', msg, False)
        blaze_button(req,ws,lock,"START_MOTOR")

        #uv4l.start_uv4l_raspicam()

        __inform_ui(ws, lock, param.LIVE_FEED_UUID, param.video_url, '')

        #uv4l.start_streaming(param.raspicam_server, param.video_room)

        

        relay_switch.switch(param.LIGHT, relay_switch.ON)
        relay_switch.switch(param.INPUT, relay_switch.ON)

        
        SD = SerialCom()

        SD.serial.port = SD.get_port('USB <-> Serial - USB <-> Serial')
        print(SD.serial.port)
        SD.serial.baudrate = 1250000
        SD.serial.parity = "N"
        SD.serial.stopbits = 1
        SD.serial.bytesize = 8
        SD.serial.timeout = 1
        #SD.bytesize=SD.serial.EIGHTBITS
        SD.serial.open()
        #SD.serial.timeout = 1
        time.sleep(0.2)
        thestring = bytearray([0x22]) #,0x0d,0x0a

        #SD.serial.write(thestring)
        print("> ", SD.serial.readline())
        #phase = bytearray([0X2E,0X10,0X01,0X00])
        #print(phase)
        #SD.serial.write(phase)

        print("> ", SD.serial.readline())
        #thestring = bytearray([0x22])
        print(thestring[0]) #,0x0d,0x0a
        
        #SD.serial.write(thestring)
        print("$ ", SD.serial.readline())

        cmd = bytearray([0xAA, 0x01, 0x00, 0x00, 0xAB])

        SD.serial.write(cmd)
        #time.sleep(1)
        data = SD.serial.read(5)
        print("$> ",data.hex())
        cmd = bytearray([0xAA, 0x10, 0x00, 0x00, 0xBA])

        SD.write(cmd)
        #time.sleep(1)
        data = SD.serial.read(5)
        print("$> ",data.hex())
        #SD.serial.close()

        # except Exception as excp:
        #     msg = "$> USB not connected "
        #     util.send_status(ws, lock, 'connect', msg, False)
        req['output_container'] = __graph_metadata()
        

        time.sleep(2)
        util.send_status(ws, lock, 'connect', "$> SYSTEM READY", False)  # NewChange
        util.send_status(ws, lock, 'connect', "$> START EVALUATING", False)  # NewChange
        req['start_time']= time.time()
    #
    try:
        # SD = SerialCom()    

        # SD.serial.port = SD.get_port('USB <-> Serial - USB <-> Serial')
        # print(SD.serial.port)
        # SD.serial.baudrate = 1250000
        # SD.serial.parity = "N"
        # SD.serial.stopbits = 1
        # SD.serial.bytesize = 8
        # SD.serial.timeout = 2
        # #SD.bytesize=SD.serial.EIGHTBITS
        # SD.serial.open()
        # #SD.serial.timeout = 2
        # #time.sleep(0.2)
        cmd = bytearray([0xAA, 0x20, 0x00, 0x00, 0xCA])
        SD.serial.write(cmd)

        data = SD.serial.read(1412)
        data = list(data)
        print("serial",data)
        if data:
        
        
            data = data[5:]
            
            #print("some",data)
        

            speed = data[5] + (data[6])*256
            
            print("here",speed)
            ang = []
            del_sin= []
            del_cos= []
            for j in range(7,1407,7):

                angle = ((data[j]) * 10 + (data[j+1])/10 + (data[j+2])/1000) % 360
                ang.append(angle)
                #print(ang)

                delta_sin = data[j+3] +(data[j+4])*256
                if (delta_sin > 32768):
                    delta_sin = delta_sin - 65535
                    delta_sin = delta_sin/4096*5
                else:
                    delta_sin = delta_sin/4096*5
                del_sin.append(delta_sin)

                delta_cos = data[j+5] + (data[j+6])*256
                if (delta_cos > 32768):
                    delta_cos = delta_cos - 65535
                    delta_cos = delta_cos/4096*5
                else:
                    delta_cos = delta_cos/4096*5
                del_cos.append(delta_cos)
            print("cos",delta_cos)
            print("sin",delta_sin)
            print("angle",len(ang))
            start_time = (time.time()-req['start_time'])
            start_time = []
            for i in range(0,200):
                start_time.append(i)
                
            print(start_time)
            list1= list(map(list, zip(start_time,ang)))
            
            print("list1", list1)

            list2= list(map(list, zip(start_time,del_cos,start_time,del_sin)))
            req['output_container'] = {
                    "metadata": {
                        "y1": {
                            "list_number": [0],
                            "type": ["line"],
                            "list_label": ["angle"],
                            "axis_label": {"x": "count ", "y": "angle"}
                        }
                    }
            }
            util.format_output(req, ws, lock, list1,[2], [True], "graph_plot1")
            req['output_container'] = {
                    "metadata": {
                        "y1": {
                            "list_number": [0,1],
                            "type": ["line","line"],
                            "list_label": ["delta_cos","delta_sin"],
                            "axis_label": {"x": "count ", "y": "value"}
                        }
                    }
            }
            util.format_output(req, ws, lock, list2,[4], [True], "graph_plot2")

        else:
            print("there is no data coming from EVM")

            

    except Exception as e:
        print(e)






    return 0.2


def direction(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])
    dire = int(req['values'])
    util.set_config_param({"direction": dire})
    if int(req['values']) == 1:
        msg = "Direction is set to clockwise"
        util.send_status(ws, lock, 'direction', msg, False)

    elif int(req['values']) == 2:
        msg = "Direction is set to counter clockwise"
        util.send_status(ws, lock, 'direction', msg, False)

    else:
        msg = "INVALID INPUT GIVEN FOR DIRECTION"
        util.send_status(ws, lock, 'direction', msg, False)


    util.relinquish_output(ws, lock)
    return util.EXIT

def speed(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])
    rpm = req['values']
    util.set_config_param({"rpm":rpm})
    msg = "Speed has been set to {0} %".format(rpm)
    util.send_status(ws, lock, 'speed', msg, False)
    
    

    util.relinquish_output(ws, lock)
    return util.EXIT


def resolution(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])
    

    util.relinquish_output(ws, lock)
    return util.EXIT

def start_button(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])
    direction = util.get_config_param("direction")
    rpm = util.get_config_param("rpm")
    print(rpm ,direction)
    if rpm != None and direction != None:
        if int(direction) == 1:
            motor.motor_run('f', duty_cycle = int(rpm))
            msg = "motor is rotating in forward direction"
            util.send_status(ws, lock, 'start_button', msg, False)
            

        elif int(direction) == 2:
            motor.motor_run('r',duty_cycle = int(rpm))
            msg = "motor is rotating in reverse direction"
            util.send_status(ws, lock, 'start_button', msg, False)


        else:
            pass




    util.relinquish_output(ws, lock)
    return util.EXIT

def reset(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])

    util.relinquish_output(ws, lock)
    return util.EXIT

def command_name(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    set the load current in custome load use case
    """
    req['elk_stack'] = None

    print("value from UI :", req['values'])

    util.relinquish_output(ws, lock)
    return util.EXIT

def ignore(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    ignore function for non-functional UI elements
    """
    req['elk_stack'] = None

    return util.EXIT


def disconnect(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    Description: Disconnect connection from UI and device.
    Args:
        req: Request from UI
        ws: Websocket address
        lock: Lock for websocket
        shared_list: List shared by other process
        queue: Memory location of the queue which contains data of the live process
    """

    req['elk_stack'] = None
    return util.EXIT


def clear_all_local_settings():
    """
    clear the config_params and prepare for the next run
    """
    return util.EXIT


def clean_up():
    """
    Clear all config params
    Args:
        lock: Lock for hardware access.
    Returns:
        None

    """
    uv4l.stop_streaming(param.raspicam_server, param.video_room)
    relay_switch.switch(param.INPUT, relay_switch.OFF)
    relay_switch.switch(param.LIGHT, relay_switch.OFF)
    return util.EXIT


def live_cleanup():
    """
    live value clean up
    :return:
    """
    return util.EXIT


def idle_session_callback():
    """
        process for post disconnection
        Called only during Idle session (User Not Connected)
        The callback interval is determined by device_constants > IDLE_CALLBACK_TIMEOUT_SEC
        This function is called until it returns 0.
    """

    return 0


############### EVM Code #############


def send_table_data(req, ws, lock,value,table_name):
    '''
    2 in the format output stands for two column in the table
    each cell in table is represented by an array of value and color
    [ 'value' : 'text to show','color': (optional)color_code] where color_code can be 'ff0000'.
    all the cells represending a row are appended to a list , Means each row is a list of list. 
    '''
    table_data = [[{'value':' Parameter Name','color':'ffffff'},{'value': 'Value','color':'ffffff'}],
        [{'value':'FLOW_RATE : ','color':'ff0000'},{'value':value,'color':'00ff00'}]]

    util.format_output(req,ws,lock,table_data,[2],[True],table_name) 


def ui_command_live_function_template(req, ws, lock, event, shared_live_queue):
    """
    live function
    """
    req['elk_stack'] = None  # Replace None with "_ANY_TEXT_" if analytics used in this function.

    # if util.get_high_priority_flag(event):        # Used for cutting of the function when priority flag set
    #     util.clear_high_priority_flag(event)      # Flag is set when user executes a feature by interrupting current process
    #     return util.EXIT

    msg = "Progress log msg"
    util.send_status(ws, lock, 'remote', msg, False)  # Progress Log

    util.relinquish_output(ws, lock)

    return util.EXIT


def ui_command_hardware_function_template(req, ws, lock, event, shared_pp_queue, shared_live_queue):
    """
    hardware function
    """
    req['elk_stack'] = None  # Replace None with "_ANY_TEXT_" if analytics used in this function.

    # if util.get_high_priority_flag(event):        # Used for cutting of the function when priority flag set
    #     util.clear_high_priority_flag(event)      # Flag is set when user executes a feature by interrupting current process
    #     return util.EXIT

    value = req['values']  # Get's value set on UI as string (str)
    util.set_config_param({'ui_value': value})  # stores the value in util for future usage

    msg = "Progress log msg"
    util.send_status(ws, lock, 'remote', msg, False)  # Progress Log

    # Analytics Formats (Use if required and remove it not)
    # util.set_analytics_feature_name('_Analytics_')
    # util.set_analytics_string_feature(1, 'string_feeature_name', 'string feature msg')
    # util.set_analytics_int_feature(1, 'int_feeature_name', 'int feature msg')
    # util.set_analytics_float_feature(1, 'float_feeature_name', 'float feature msg')

    _end_of_feature(ws, lock)  # Indicates end of feature with a short line
    util.relinquish_output(ws, lock)

    return util.EXIT
