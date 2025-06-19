# MicroPython script for Qube Microbit
def sendStatus(status: str):
    radio.send_string(convert_to_text("L" + "," + ("" + str(leerlingnummer)) + "," + status))
    radio.send_string(convert_to_text("L" + "," + ("" + str(leerlingnummer)) + "," + status))
def animatie():
    basic.show_leds("""
        . . . . .
        . . . . .
        . . . . .
        . . . . .
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        . . . . .
        . . . . .
        . . . . .
        # # . # #
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        . . . . .
        . . . . .
        # # . # #
        # # # # #
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        . . . . .
        . . . . .
        # # . # #
        # # # # #
        # # # # #
        """)
    basic.pause(10)
    basic.show_leds("""
        . . . . .
        . . . . .
        # # # # #
        # # # # #
        # # # # #
        """)
    basic.pause(10)
    basic.show_leds("""
        . . . . .
        . . # . .
        # # # # #
        # # # # #
        # # # # #
        """)
    basic.pause(10)
    basic.show_leds("""
        . . . . .
        # # # # #
        # # # # #
        # # # # #
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        # # # # #
        # # # # #
        # # # # #
        # # # # #
        # # # # #
        """)
    basic.pause(30)
    basic.show_leds("""
        # # # # #
        # # # # #
        # # . # #
        # # # # #
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        # # # # #
        # # . # #
        # . . . #
        # # . # #
        # # # # #
        """)
    basic.pause(20)
    basic.show_leds("""
        # # . # #
        # . . . #
        . . . . .
        # . . . #
        # # . # #
        """)
    basic.pause(20)
    basic.show_leds("""
        # . . . #
        . . . . .
        . . . . .
        . . . . .
        # . . . #
        """)
    basic.pause(10)
    basic.show_leds("""
        . . . . .
        . . . . .
        . . . . .
        . . . . .
        . . . . .
        """)
def setup():
    global lln_cursor2, getal, lijst, leerlingnummer
    basic.show_string("SETUP!")
    lln_cursor2 = 0
    getal = 0
    lijst = [0, 0, 0, 0, 0, 0]
    for lln_cursor in range(6):
        basic.show_string("" + str(getal))
        while not (input.logo_is_pressed()):
            if input.button_is_pressed(Button.B):
                getal += 1
                if getal < 0:
                    getal = 9
                if getal > 9:
                    getal = 0
                lijst[lln_cursor] = Math.constrain(getal, 0, 9)
                basic.show_string("" + str(Math.constrain(getal, 0, 9)))
            elif input.button_is_pressed(Button.A):
                getal += -1
                if getal < 0:
                    getal = 9
                if getal > 9:
                    getal = 0
                lijst[lln_cursor] = Math.constrain(getal, 0, 9)
                basic.show_string("" + str(Math.constrain(getal, 0, 9)))
        getal = 0
        basic.show_icon(IconNames.YES)
        basic.pause(100)
    leerlingnummer = 0
    for waarde in lijst:
        leerlingnummer = leerlingnummer * 10 + waarde
    flashstorage.put("LEERLINGNUMMER", convert_to_text(leerlingnummer))
    basic.show_icon(IconNames.HEART)
    basic.show_string("LLN:")
    basic.show_string("" + str(leerlingnummer))
    basic.show_icon(IconNames.CHESSBOARD)
    basic.pause(100)
    basic.clear_screen()
lijst: List[number] = []
getal = 0
lln_cursor2 = 0
leerlingnummer = 0
leerlingnummer = parse_float(flashstorage.get_or_default("LEERLINGNUMMER", ""))
radio.set_group(147)
radio.set_transmit_power(7)
status2 = "G"
if not (leerlingnummer):
    animatie()
    setup()
else:
    basic.show_string("" + str(leerlingnummer))

def on_forever():
    global status2
    if input.button_is_pressed(Button.A) and input.button_is_pressed(Button.B) and input.logo_is_pressed():
        setup()
    if input.is_gesture(Gesture.SCREEN_DOWN):
        if status2 != "G":
            status2 = "G"
            sendStatus(status2)
    elif input.is_gesture(Gesture.LOGO_UP):
        if status2 != "V":
            status2 = "V"
            sendStatus(status2)
    elif input.is_gesture(Gesture.SCREEN_UP):
        if status2 != "R":
            status2 = "R"
            sendStatus(status2)
basic.forever(on_forever)

def on_every_interval():
    sendStatus(status2)
loops.every_interval(30000, on_every_interval) # Every 30 seconds, send the current status
