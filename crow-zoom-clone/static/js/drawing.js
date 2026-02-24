// ✏️ drawing.js - Finger Drawing Feature for Crow Video Room
// Uses MediaPipe Hands for finger tracking + WebSocket for real-time sync

// ─── State ───────────────────────────────────────────────────────────────────
const drawingState = {
    enabled: false,
    isDrawing: false,
    tool: 'pen',       // 'pen' | 'eraser'
    color: '#00d4ff',
    brushSize: 4,
    lastX: null,
    lastY: null,
    hands: null,
    camera: null,
    animationId: null,
    hiddenVideo: null,
};

// ─── Canvas Setup ─────────────────────────────────────────────────────────────
let drawCanvas, drawCtx;

function initDrawingCanvas() {
    drawCanvas = document.getElementById('drawingCanvas');
    if (!drawCanvas) return;
    drawCtx = drawCanvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    if (!drawCanvas) return;
    drawCanvas.width = window.innerWidth;
    drawCanvas.height = window.innerHeight;
}

// ─── MediaPipe Setup ──────────────────────────────────────────────────────────
async function initMediaPipe() {
    // Load MediaPipe from CDN
    await loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.js');
    await loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.3.1675466862/camera_utils.js');

    drawingState.hiddenVideo = document.getElementById('drawingHiddenVideo');

    drawingState.hands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${file}`
    });

    drawingState.hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.7,
    });

    drawingState.hands.onResults(onHandResults);

    drawingState.camera = new Camera(drawingState.hiddenVideo, {
        onFrame: async () => {
            if (drawingState.enabled) {
                await drawingState.hands.send({ image: drawingState.hiddenVideo });
            }
        },
        width: 640,
        height: 480
    });

    await drawingState.camera.start();
}

// ─── Hand Detection Results ───────────────────────────────────────────────────
function onHandResults(results) {
    if (!drawingState.enabled || !results.multiHandLandmarks?.length) {
        drawingState.isDrawing = false;
        drawingState.lastX = null;
        drawingState.lastY = null;
        hideCursor();
        return;
    }

    const landmarks = results.multiHandLandmarks[0];

    // Index fingertip = landmark 8
    // Middle fingertip = landmark 12
    const indexTip = landmarks[8];
    const middleTip = landmarks[12];
    const indexMcp = landmarks[5];  // Index base

    // Mirror X because camera is mirrored
    const x = (1 - indexTip.x) * window.innerWidth;
    const y = indexTip.y * window.innerHeight;

    // Gesture: index UP + middle DOWN = draw
    // (index tip above its base, middle tip below index tip = drawing mode)
    const indexUp = indexTip.y < indexMcp.y - 0.05;
    const middleDown = middleTip.y > indexTip.y + 0.03;
    const shouldDraw = indexUp && middleDown;

    // Show live cursor dot
    showCursor(x, y, shouldDraw);

    if (shouldDraw) {
        if (drawingState.lastX !== null) {
            drawLine(
                drawingState.lastX,
                drawingState.lastY,
                x, y,
                drawingState.color,
                drawingState.brushSize,
                drawingState.tool,
                true // broadcast
            );
        }
        drawingState.lastX = x;
        drawingState.lastY = y;
        drawingState.isDrawing = true;
    } else {
        drawingState.lastX = null;
        drawingState.lastY = null;
        drawingState.isDrawing = false;
    }
}

// ─── Drawing Functions ────────────────────────────────────────────────────────
function drawLine(x1, y1, x2, y2, color, size, tool, broadcast = false) {
    if (!drawCtx) return;

    drawCtx.save();
    drawCtx.beginPath();
    drawCtx.moveTo(x1, y1);
    drawCtx.lineTo(x2, y2);
    drawCtx.strokeStyle = tool === 'eraser' ? 'rgba(0,0,0,1)' : color;
    drawCtx.lineWidth = tool === 'eraser' ? size * 6 : size;
    drawCtx.lineCap = 'round';
    drawCtx.lineJoin = 'round';

    if (tool === 'eraser') {
        drawCtx.globalCompositeOperation = 'destination-out';
    } else {
        drawCtx.globalCompositeOperation = 'source-over';
        // Glow effect
        drawCtx.shadowBlur = 8;
        drawCtx.shadowColor = color;
    }

    drawCtx.stroke();
    drawCtx.restore();

    if (broadcast) {
        broadcastDraw({ x1, y1, x2, y2, color, size, tool });
    }
}

function clearCanvas(broadcast = false) {
    if (drawCtx) {
        drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    }
    if (broadcast) {
        broadcastDraw({ action: 'clear' });
    }
}

// ─── Cursor Indicator ─────────────────────────────────────────────────────────
function showCursor(x, y, active) {
    let cursor = document.getElementById('drawCursor');
    if (!cursor) {
        cursor = document.createElement('div');
        cursor.id = 'drawCursor';
        cursor.style.cssText = `
            position: fixed;
            pointer-events: none;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.1s, height 0.1s;
            z-index: 9999;
        `;
        document.body.appendChild(cursor);
    }

    const size = drawingState.tool === 'eraser' ? drawingState.brushSize * 6 : drawingState.brushSize * 2 + 8;
    cursor.style.left = x + 'px';
    cursor.style.top = y + 'px';
    cursor.style.width = size + 'px';
    cursor.style.height = size + 'px';
    cursor.style.background = active
        ? (drawingState.tool === 'eraser' ? 'rgba(255,255,255,0.3)' : drawingState.color + '80')
        : 'transparent';
    cursor.style.border = `2px solid ${drawingState.tool === 'eraser' ? '#fff' : drawingState.color}`;
    cursor.style.display = 'block';
}

function hideCursor() {
    const cursor = document.getElementById('drawCursor');
    if (cursor) cursor.style.display = 'none';
}

// ─── WebSocket Broadcast ──────────────────────────────────────────────────────
function broadcastDraw(data) {
    if (typeof sendSignal === 'function') {
        sendSignal({ type: 'draw', data });
    }
}

// Call this from the main WS onmessage handler
function handleDrawMessage(data) {
    if (data.action === 'clear') {
        clearCanvas(false);
        return;
    }
    const { x1, y1, x2, y2, color, size, tool } = data;
    drawLine(x1, y1, x2, y2, color, size, tool, false);
}

// ─── Toggle Drawing Mode ──────────────────────────────────────────────────────
async function toggleDrawingMode() {
    drawingState.enabled = !drawingState.enabled;
    const btn = document.getElementById('drawingBtn');
    const toolbar = document.getElementById('drawingToolbar');

    if (drawingState.enabled) {
        // First time: init mediapipe
        if (!drawingState.hands) {
            showToast('Loading hand tracking...');
            try {
                await initMediaPipe();
                showToast('✋ Hand tracking ready! Point your index finger to draw');
            } catch (e) {
                console.error('MediaPipe init failed:', e);
                showToast('Could not start hand tracking');
                drawingState.enabled = false;
                return;
            }
        }

        btn.classList.add('active');
        toolbar.classList.add('visible');
        drawCanvas.style.pointerEvents = 'none';
        showToast('✏️ Drawing mode ON — index finger up to draw, pinch off to pause');
    } else {
        btn.classList.remove('active');
        toolbar.classList.remove('visible');
        hideCursor();
        drawingState.lastX = null;
        drawingState.lastY = null;
        showToast('Drawing mode OFF');
    }
}

// ─── Toolbar Controls ─────────────────────────────────────────────────────────
function initDrawingToolbar() {
    document.getElementById('drawColorPicker').addEventListener('input', (e) => {
        drawingState.color = e.target.value;
    });

    document.getElementById('drawBrushSize').addEventListener('input', (e) => {
        drawingState.brushSize = parseInt(e.target.value);
        document.getElementById('brushSizeLabel').textContent = e.target.value;
    });

    document.getElementById('drawToolPen').addEventListener('click', () => {
        drawingState.tool = 'pen';
        document.getElementById('drawToolPen').classList.add('active');
        document.getElementById('drawToolEraser').classList.remove('active');
    });

    document.getElementById('drawToolEraser').addEventListener('click', () => {
        drawingState.tool = 'eraser';
        document.getElementById('drawToolEraser').classList.add('active');
        document.getElementById('drawToolPen').classList.remove('active');
    });

    document.getElementById('drawClearBtn').addEventListener('click', () => {
        clearCanvas(true);
    });

    document.getElementById('drawingBtn').addEventListener('click', toggleDrawingMode);
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) return resolve();
        const s = document.createElement('script');
        s.src = src;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
    });
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initDrawingCanvas();
    initDrawingToolbar();
});