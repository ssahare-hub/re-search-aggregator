// TODO: Change UI
// Socket connection variable
var socket;
// Messages to display as INFO logs
const WAIT_CONNECT_MSG = 'Establishing connection with server...'
const START_PROCESS_MSG = 'URL received, processing has been started';
const CONTINUE_PROCESS_MSG = 'Info about results processed is -> ';
// Connecting to web sockets
function connect() {
    var url = 'http://' + document.domain + ':' + location.port
    console.log('url', url)
    socket = io.connect(url);
    console.log('socket id ', socket['id']);
    var counter = 0;
    // start of socket event listeners
    socket.on('connect', function () {
        // on upload start, change message
        console.log('connected socket-io');
        const SERVER_ESTB_MSG = 'Connection with server established...';
        displayMessage(SERVER_ESTB_MSG);
        addToDiv('logs', SERVER_ESTB_MSG)
    });

    socket.on('upload_start', (data) => {
        console.log('upload_Start')
        const START_UPLOAD_MSG = `Uploading of ${data} valid images started, waiting on processing...`;
        displayMessage(START_UPLOAD_MSG);
        addToDiv('logs', START_UPLOAD_MSG)
    });

    // on processing start, change message
    socket.on('processing_start', (all) => {
        console.log('processing_start, job length ->', all)
        counter = 0;
        displayMessage(START_PROCESS_MSG);
        addToDiv('logs', START_PROCESS_MSG);
    });

    // on processing end, change message
    socket.on('processing_end', () => {
        console.log('processing_end')
        const END_PROCESS_MSG = 'Processing Complete, all results have loaded below -> ';
        displayMessage(END_PROCESS_MSG);
        addToDiv('logs', END_PROCESS_MSG);
    })
    // on disconnect show connect option ->
    socket.on('disconnect', () => {
        console.log('disconnected')
        const DISC_MSG = 'Connection to server has been lost, retrying connection...';
        displayMessage(DISC_MSG);
        addToDiv('logs', DISC_MSG);
    })
    // show results as they arrive
    socket.on('partial_result', (response) => {
        var respObj = JSON.parse(response)
        counter += 1;
        // TODO: Change UI
        var msg = `<strong>${counter}) ${respObj.name} - ${respObj.email}</strong> <br> ${respObj.links}<br>`;
        arrangeInDiv('results', msg, 'col')
        var message = CONTINUE_PROCESS_MSG + `${counter} / ${respObj.total}`;
        displayMessage(message);
    })
}

connect()

// helper functions
function displayMessage(message) {
    var x = document.getElementById('info');
    if (x) {
        x.innerText = '[INFO] ' + message;
    }
}

function addToDiv(div_id, message, className = '') {
    var x = document.getElementById(div_id)
    if (x) {
        var y = document.createElement('p')
        y.innerText = message
        y.className = className
        x.appendChild(y)
    }
}

// alignment and arrangement of results logic
const DIV_PREFIX = 'log-container-';
const MAX_IN_DIV = 3;
var div_id_num = 1
var last_div = document.getElementById('log-container-1'), last_div_count = 0;
function arrangeInDiv(div_id, message, className = '') {
    if (last_div_count >= MAX_IN_DIV) {
        last_div = document.createElement('div');
        div_id_num += 1;
        last_div.id = DIV_PREFIX + div_id_num;
        last_div.className = 'row'
        console.log(last_div.id)
        var x = document.getElementById(div_id)
        console.log(x)
        x.appendChild(last_div);
        last_div_count = 0;
    }
    last_div_count += 1;
    var y = document.createElement('div')
    y.innerHTML = message
    y.className = className
    last_div.appendChild(y)
}

// local testing generator
function generator() {
    random_results = [
        'im_copy_age.jpeg==result_2342',
        'image.jpeg==result_sdddsaas',
        'image.jpeg==result',
        'image0.jpeg==result2413',
        'image12.jpeg==resultasdf',
        'image1.jpeg==resulta',
        'image22.jpeg==rest',
        'image4_copy.jpeg==resu asdlt',
        'image53.jpeg==result  asd',
        'image_copy.jpeg==reslt',
    ]
    for (i = 0; i < 100; i++) {
        var x = Math.floor(Math.random() * 10)
        var msg = `<strong>${i + 1})</strong> ${random_results[x]}`;
        arrangeInDiv("results", msg, 'col');
    }
}