var key_names = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'A\u266d']

function pC(c) {
    return c.replace('b', '\u266d').replace('#', '\u266f')
}

function n2c(n) {
    return key_names[n % 12];
}

function keyScrollUp(allowRollover) {
    /* Scroll by 1/2 window height each button press */
    var n = window.innerHeight / 2;
    
    if (window.scrollY <= 5 && allowRollover)
    {
        if (typeof prev == "function")
        {
            prev();
        }
    }
    else
    {
        new_scroll_loc = window.scrollY - n;
        $("html, body").animate({ scrollTop: new_scroll_loc }, 200);
    }
}
function keyScrollDown(allowRollover) {
    /* Scroll by 1/2 window height each button press */
    var n = window.innerHeight / 2;

    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 5 && allowRollover)
    {
        if (typeof next == "function")
        {
            next();
        }
    }
    else
    {
        new_scroll_loc = window.scrollY + n;
        $("html, body").animate({ scrollTop: new_scroll_loc }, 200);
    }
}

function processKeyPress(e) {
    e = e || window.event;

    if (['input', 'textarea', 'select', 'button'].indexOf(document.activeElement.tagName.toLowerCase()) == -1)
    {
        if (e.key == 'PageUp' || e.key == 'ArrowUp') {
            e.preventDefault();
            keyScrollUp(true);
        }
        else if (e.key == 'PageDown' || e.key == 'ArrowDown') {
            e.preventDefault();
            keyScrollDown(true);
        }
    }
}


/* Try and initialise midi listening if the browser supports it */
/* Initial hardcoded midi messages:
 *   C7 00   - Program Change, Chan 8, Val 0 - Scroll Up w/ rollover
 *   C7 01   - Program Change, Chan 8, Val 1 - Scroll Down w/ rollover
 *   C7 02   - Program Change, Chan 8, Val 2 - Scroll Up w/o rollover
 *   C7 03   - Program Change, Chan 8, Val 3 - Scroll Down w/o rollover
 *   C7 04   - Program Change, Chan 8, Val 4 - Previous Song
 *   C7 05   - Program Change, Chan 8, Val 5 - Next Song
 */
let pc_channel = 8;
function onMidiMessage(e) {
    // PC is a 2 byte message, looking for 0xC0 + pc_channel as the first byte
    if (e.data.length == 2) 
    {
        midi_byte1 = e.data[0];
        console.log("Midi message identifier is 0x" + midi_byte1.toString(16));

        if (midi_byte1 == (0xC0 + (pc_channel - 1))) 
        {
            // confirmed PC message on the correct channel
            pc_value = e.data[1];
            console.log("PC detected on our channel. Value is " + pc_value.toString(16));

            if (pc_value == 0x00) { keyScrollUp(true); }
            if (pc_value == 0x01) { keyScrollDown(true); }
            if (pc_value == 0x02) { keyScrollUp(false); }
            if (pc_value == 0x03) { keyScrollDown(false); }
            if (pc_value == 0x04) { prev(); }
            if (pc_value == 0x05) { next(); }
        }
    }
}

$(function() {
    navigator.requestMIDIAccess().then(function(midi) {
        console.log("Gained MIDI access");

        midi.inputs.forEach((entry) => {
            console.log("Adding message listener to " + entry.name);
            entry.onmidimessage = onMidiMessage;
        });
    })
});