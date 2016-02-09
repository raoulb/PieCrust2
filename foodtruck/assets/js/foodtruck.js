
$(document).ready(function() {
    $('.ft-nav-toggle').click(function() {
        $('.ft-nav-container').toggleClass('ft-nav-enabled');
        $('.ft-nav').toggleClass('ft-nav-enabled');
    });

    $('.ft-nav-collapsed + ul').hide();

    $('#ft-commit-modal').on('shown.bs.modal', function () {
        $('#ft-commit-msg').focus();
    });

    var publogEl = $('#ft-publog');
    publogEl.mouseenter(function() {
        publogEl.attr('data-autohide', 'false');
    });
    publogEl.on('hide', function() {
        var containerEl = $('#ft-publog-container', publogEl);
        containerEl.empty();
    });

    var closePublogBtn = $('button', publogEl);
    closePublogBtn.on('click', function() {
        publogEl.fadeOut(200);
    });
});

var onPublishEvent = function(e) {

    var publogEl = $('#ft-publog');
    var containerEl = $('#ft-publog-container', publogEl);

    var msgEl = $('<div>' + e.data + '</div>');
    var removeMsgEl = function() {
        msgEl.remove();
        if (containerEl.children().length == 0) {
            // Last message, hide the log window.
            publogEl.fadeOut(200);
        }
    };
    var timeoutId = window.setTimeout(function() {
        if (publogEl.attr('data-autohide') == 'true') {
            msgEl.fadeOut(400, removeMsgEl);
        }
    }, 4000);

    if (containerEl.children().length == 0) {
        // First message, show the log window, reset the mouseover marker.
        publogEl.attr('data-autohide', 'true');
        publogEl.fadeIn(200);
    }
    containerEl.append(msgEl);
};

if (!!window.EventSource) {
    var source = new EventSource('/publish-log');
    source.onerror = function(e) {
        console.log("Error with SSE, closing.", e);
        source.close();
    };
    source.addEventListener('message', onPublishEvent);
}

