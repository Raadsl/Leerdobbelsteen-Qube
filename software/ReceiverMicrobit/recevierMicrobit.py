# MicroPython script for Receiver Microbit

def on_received_string(receivedString):
    serial.write_line(receivedString)
radio.on_received_string(on_received_string)

def on_data_received():
    radio.send_string(serial.read_line())
serial.on_data_received(serial.delimiters(Delimiters.NEW_LINE), on_data_received)

radio.set_group(147) # moet hetzeflde zijn als QubeMicrobit

def on_forever():
    pass
basic.forever(on_forever)
