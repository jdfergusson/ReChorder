var key_names = ['A', 'B\u266d', 'B', 'C', 'C\u266f', 'D', 'E\u266d', 'E', 'F', 'F\u266f', 'G', 'A\u266d']

function pC(c) {
    return c.replace('b', '\u266d').replace('#', '\u266f')
}

function n2c(n) {
    return key_names[n % 12];
}

function processKeyPress(e) {
    e = e || window.event;

    /* Scroll by 1/2 window height each button press */
    var n = window.innerHeight / 2;

    if (['input', 'textarea', 'select', 'button'].indexOf(document.activeElement.tagName.toLowerCase()) == -1)
    {
        if (e.key == 'PageUp' || e.key == 'ArrowUp') {
            e.preventDefault();
            if (window.scrollY <= 5)
            {
                if (typeof prev == "function")
                {
                    prev();
                }
            }
            else
            {
                new_scroll_loc = windows.scrollY - n;
                $("html, body").animate({ scrollTop: new_scroll_loc }, 200);
            }
        }
        else if (e.key == 'PageDown' || e.key == 'ArrowDown') {
            e.preventDefault();
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 5)
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
    }
}
