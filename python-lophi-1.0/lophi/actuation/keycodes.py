"""
    Function for converting keys to their appropriate codes

    (c) 2015 Massachusetts Institute of Technology
"""

# "Key":keycode
def get_codes(cmd):
    """
        Will convert a string to the actual keycodes used by libvirt to type 
        that text.
        
        @param cmd: String to be converted into keycodes
        @return: List of keycodes used to type the input string
    """
    keys = []
    
    for c in cmd:
        
        # Is this a capital character?
        if c.isupper():
            shift = True
        else:
            shift = False
            
        # All indicies are uper
        c = c.upper()
        if c in KEYCODES:
            if shift:
                keys.append([ KEYCODES['L_SHIFT'], KEYCODES[c] ])
            else:
                keys.append(KEYCODES[c])
                
        # Is this a special shift char?
        elif c in SHIFT_KEYCODES:
            shifted_key = SHIFT_KEYCODES[c]
            keys.append([ KEYCODES['L_SHIFT'], KEYCODES[shifted_key] ])
            
        else:
            print "* Oops: %s not in KEYCODES." % c
    return keys

SHIFT_KEYCODES = {
"_":"-",
"\"":"'",
"!":"1",
":":";"
}

KEYCODES = {
"ESC":1,
"1":2,
"2":3,
"3":4,
"4":5,
"5":6,
"6":7,
"7":8,
"8":9,
"9":10,
"0":11,
"-":12,
"=":13,
"BS":14,
"TAB":15,
"Q":16,
"W":17,
"E":18,
"R":19,
"T":20,
"Y":21,
"U":22,
"I":23,
"O":24,
"P":25,
"[":26,
"]":27,
"RETURN":28,
"L_CTRL":29,
"A":30,
"S":31,
"D":32,
"F":33,
"G":34,
"H":35,
"J":36,
"K":37,
"L":38,
";":39,
"'":40,
"`":41,
"L_SHIFT":42,
"\\":43,
"Z":44,
"X":45,
"C":46,
"V":47,
"B":48,
"N":49,
"M":50,
",":51,
".":52,
"/":53,
"R_SHIFT":54,
"*":55,
"LEFT_ALT":56,
"SPACE":57,
" ":57,
"CAPS_LOCK":58,
"F1":59,
"F2":60,
"F3":61,
"F4":62,
"F5":63,
"F6":64,
"F7":65,
"F8":66,
"F9":67,
"F10":68,
"NUM_LOCK":69,
"SCROLL_LOCK":70,
"HOME":71,
"UP":72,
"PGUP":73,
#"-":74,
"LEFT":75,
#"5":76,
"RT_ARROW":77,
"+":78,
"END_1":79,
"DOWN_2":80,
"PGDN_3":81,
"INS":82,
"DEL":84,
#84                        
#85                        
#86                        
"F11":87,
"F12":88,
#89                        
#90                        
#91                        
#92                        
#93                        
#94                        
#95                        
"R_ENTER":96,
"R_CTRL":97,
"/":98,
"PRT_SCR":99,
"R_ALT":100,
#101                        
"Home":102,
"Up":103,
"PgUp":104,
"Left":105,
"Right":106,
"End":107,
"Down":108,
"PgDn":109,
"Insert":110,
"Del":111,
#112                        
#113                        
#114                        
#115                        
#116                        
#117                        
#118                        
"Pause":119,
"LEFT_GUI":(133 - 8)}


"""
    Keymap used for Arduino Special Characters
"""
ARDUINO_KEYMAP = {

# Key                    Hexadecimal value    Decimal value
'LEFT_CTRL':            ('0x80', '128'),
'LEFT_SHIFT':            ('0x81', '129'),
'LEFT_ALT':            ('0x82', '130'),
'LEFT_GUI':            ('0x83', '131'),
'RIGHT_CTRL':           ('0x84', '132'),
'RIGHT_SHIFT':            ('0x85', '133'),
'RIGHT_ALT':            ('0x86', '134'),
'RIGHT_GUI':            ('0x87', '135'),
'UP_ARROW':            ('0xDA', '218'),
'DOWN_ARROW':            ('0xD9', '217'),
'LEFT_ARROW':            ('0xD8', '216'),
'RIGHT_ARROW':            ('0xD7', '215'),
'BACKSPACE':            ('0xB2', '178'),
'TAB':                    ('0xB3', '179'),
'RETURN':            ('0xB0', '176'),
'ESC':                    ('0xB1', '177'),
'INSERT':               ('0xD1', '209'),
'DELETE':            ('0xD4', '212'),
'PAGE_UP':            ('0xD3', '211'),
'PAGE_DOWN':            ('0xD6', '214'),
'HOME':                    ('0xD2', '210'),
'END':                  ('0xD5', '213'),
'CAPS_LOCK':            ('0xC1', '193'),
'F1':                    ('0xC2', '194'),
'F2':                    ('0xC3', '195'),
'F3':                    ('0xC4', '196'),
'F4':                    ('0xC5', '197'),
'F5':                    ('0xC6', '198'),
'F6':                    ('0xC7', '199'),
'F7':                    ('0xC8', '200'),
'F8':                    ('0xC9', '201'),
'F9':                    ('0xCA', '202'),
'F10':                    ('0xCB', '203'),
'F11':                    ('0xCC', '204'),
'F12':                    ('0xCD', '205')
}
