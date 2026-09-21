// ========== 常量 ==========
const CELL = 56;          // 每个格子像素（手机上也清晰）
const HEARTS_MAX = 3;

const DIRS = {
    up:    { dr: -1, dc: 0,  ch: '↑' },
    down:  { dr: 1,  dc: 0,  ch: '↓' },
    left:  { dr: 0,  dc: -1, ch: '←' },
    right: { dr: 0,  dc: 1,  ch: '→' },
};

const CHAR_TO_DIR = { '↑': 'up', '↓': 'down', '←': 'left', '→': 'right' };

// ========== 关卡数据（对应 levels.py） ==========
const LEVELS = [
    {
        name: '第 1 关 · 新手引导',
        grid: [
            '·····',
            '·→·↑·',
            '··→··',
            '·↓·←·',
            '·····',
        ],
    },
    {
        name: '第 2 关',
        grid: [
            '······',
            '·→→·↑·',
            '······',
            '·←·↓·→',
            '······',
            '······',
        ],
    },
    {
        name: '第 3 关',
        grid: [
            '·······',
            '·→→·↑··',
            '·······',
            '·←·↓·→·',
            '·······',
            '·←·→···',
            '·······',
        ],
    },
    {
        name: '第 4 关',
        grid: [
            '········',
            '·→→→↑···',
            '········',
            '··↑··↓··',
            '········',
            '···←←←←·',
            '········',
            '········',
        ],
    },
    {
        name: '第 5 关',
        grid: [
            '←···→···',
            '·↑↑·····',
            '········',
            '··←····→',
            '←··↑→···',
            '·↑→··↓··',
            '·←↓····↓',
            '·↑··↓·→·',
        ],
    },
];

// ========== 工具函数 ==========
function parseGrid(grid) {
    const arrows = [];
    for (let r = 0; r < grid.length; r++) {
        for (let c = 0; c < grid[r].length; c++) {
            const ch = grid[r][c];
            if (CHAR_TO_DIR[ch]) {
                arrows.push({ r, c, dir: CHAR_TO_DIR[ch], blocked: false, flying: false });
            }
        }
    }
    return arrows;
}

function findBlocker(arrow, arrows) {
    const { dr, dc } = DIRS[arrow.dir];
    const occupied = new Set(
        arrows.filter(a => !(a.r === arrow.r && a.c === arrow.c)).map(a => `${a.r},${a.c}`)
    );
    let rr = arrow.r + dr;
    let cc = arrow.c + dc;
    while (rr >= 0 && rr < state.rows && cc >= 0 && cc < state.cols) {
        if (occupied.has(`${rr},${cc}`)) return { r: rr, c: cc };
        rr += dr;
        cc += dc;
    }
    return null;
}

function isSolvable(grid) {
    const rows = grid.length;
    const cols = grid[0].length;
    const arrows = [];
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            if (CHAR_TO_DIR[grid[r][c]]) arrows.push({ r, c, dir: CHAR_TO_DIR[grid[r][c]] });
        }
    }
    let changed = true;
    while (arrows.length && changed) {
        changed = false;
        for (let i = arrows.length - 1; i >= 0; i--) {
            const a = arrows[i];
            const { dr, dc } = DIRS[a.dir];
            const occupied = new Set(
                arrows.filter(x => !(x.r === a.r && x.c === a.c)).map(x => `${x.r},${x.c}`)
            );
            let rr = a.r + dr, cc = a.c + dc, blocked = false;
            while (rr >= 0 && rr < rows && cc >= 0 && cc < cols) {
                if (occupied.has(`${rr},${cc}`)) { blocked = true; break; }
                rr += dr; cc += dc;
            }
            if (!blocked) { arrows.splice(i, 1); changed = true; }
        }
    }
    return arrows.length === 0;
}

function generateRandomLevel(levelNum) {
    const rows = 8, cols = 8, arrowCount = 14;
    const dirs = ['↑', '↓', '←', '→'];
    for (let attempt = 0; attempt < 300; attempt++) {
        const grid = Array.from({ length: rows }, () => Array(cols).fill('·'));
        const cells = [];
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) cells.push([r, c]);
        cells.sort(() => Math.random() - 0.5);
        for (let i = 0; i < arrowCount; i++) {
            const [r, c] = cells[i];
            grid[r][c] = dirs[Math.floor(Math.random() * 4)];
        }
        const gridStr = grid.map(row => row.join(''));
        if (isSolvable(gridStr)) {
            return { name: `无尽模式 · 第 ${levelNum} 关`, grid: gridStr };
        }
    }
    // 保底
    return {
        name: `无尽模式 · 第 ${levelNum} 关`,
        grid: [
            '········',
            '·→→→↑···',
            '········',
            '··↑··↓··',
            '········',
            '···←←←←·',
            '········',
            '········',
        ],
    };
}

// ========== 游戏状态 ==========
const state = {
    levelIndex: 0,
    endlessNum: 1,
    endless: false,
    rows: 0,
    cols: 0,
    hearts: HEARTS_MAX,
    arrows: [],
    message: '',
    messageTimer: 0,
};

const canvas = document.getElementById('board');
const ctx = canvas.getContext('2d');

function loadLevel(level, endless = false) {
    state.endless = endless;
    state.levelIndex = 0;
    state.rows = level.grid.length;
    state.cols = level.grid[0].length;
    state.arrows = parseGrid(level.grid);
    state.hearts = HEARTS_MAX;
    state.message = '';
    state.currentLevel = level;
    resizeCanvas();
    updateHUD();
    draw();
}

function resizeCanvas() {
    const maxW = Math.min(window.innerWidth - 32, 480);
    const cellSize = Math.floor(maxW / state.cols);
    canvas.width = cellSize * state.cols;
    canvas.height = cellSize * state.rows;
    canvas.style.width = canvas.width + 'px';
    canvas.style.height = canvas.height + 'px';
    state.cellSize = cellSize;
}

function updateHUD() {
    document.getElementById('level-name').textContent = state.currentLevel.name;
    document.getElementById('hearts').textContent = '❤'.repeat(state.hearts) + '♡'.repeat(HEARTS_MAX - state.hearts);
}

// ========== 绘制 ==========
function draw() {
    const cs = state.cellSize;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 网格
    for (let r = 0; r < state.rows; r++) {
        for (let c = 0; c < state.cols; c++) {
            ctx.fillStyle = 'rgba(255,255,255,0.6)';
            ctx.fillRect(c * cs, r * cs, cs, cs);
            ctx.strokeStyle = 'rgba(200,210,225,1)';
            ctx.lineWidth = 1;
            ctx.strokeRect(c * cs, r * cs, cs, cs);
        }
    }

    // 箭头
    for (const a of state.arrows) {
        if (a.flying) continue;
        const cx = a.c * cs + cs / 2 + (a.offsetX || 0);
        const cy = a.r * cs + cs / 2 + (a.offsetY || 0);
        drawArrow(cx, cy, a.dir, cs * 0.34, a.blocked ? '#e63c3c' : '#2d78eb');
    }

    // 提示文字
    if (state.message) {
        document.getElementById('message').textContent = state.message;
    } else {
        document.getElementById('message').textContent = '';
    }
}

function drawArrow(cx, cy, dir, r, color) {
    let pts;
    if (dir === 'right') pts = [[cx + r, cy], [cx - r * 0.6, cy - r * 0.8], [cx - r * 0.6, cy + r * 0.8]];
    else if (dir === 'left') pts = [[cx - r, cy], [cx + r * 0.6, cy - r * 0.8], [cx + r * 0.6, cy + r * 0.8]];
    else if (dir === 'up') pts = [[cx, cy - r], [cx - r * 0.8, cy + r * 0.6], [cx + r * 0.8, cy + r * 0.6]];
    else pts = [[cx, cy + r], [cx - r * 0.8, cy - r * 0.6], [cx + r * 0.8, cy - r * 0.6]];

    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
}

// ========== 点击处理 ==========
canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const c = Math.floor(x / state.cellSize);
    const r = Math.floor(y / state.cellSize);
    if (r < 0 || r >= state.rows || c < 0 || c >= state.cols) return;
    handleCellClick(r, c);
});

function handleCellClick(r, c) {
    const arrow = state.arrows.find(a => a.r === r && a.c === c && !a.flying);
    if (!arrow) return;

    const blocker = findBlocker(arrow, state.arrows);
    if (blocker === null) {
        // 飞出
        arrow.flying = true;
        state.arrows = state.arrows.filter(a => a !== arrow);

        if (state.arrows.length === 0) {
            state.message = '过关！';
            updateHUD();
            draw();
            setTimeout(() => {
                if (state.endless) {
                    state.endlessNum += 1;
                    loadLevel(generateRandomLevel(state.endlessNum), true);
                } else {
                    state.levelIndex += 1;
                    if (state.levelIndex < LEVELS.length) {
                        loadLevel(LEVELS[state.levelIndex]);
                    } else {
                        state.message = '恭喜通关！';
                        updateHUD();
                    }
                }
            }, 500);
        } else {
            draw();
        }
    } else {
        // 被阻挡
        state.hearts -= 1;
        if (state.hearts <= 0) {
            state.hearts = 0;
            state.message = '游戏失败，请点击重新开始';
            updateHUD();
            draw();
            return;
        }
        state.message = '被挡住了！';
        // 简单抖动效果
        arrow.blocked = true;
        draw();
        setTimeout(() => {
            arrow.blocked = false;
            state.message = '';
            updateHUD();
            draw();
        }, 400);
    }
}

// ========== 按钮 ==========
document.getElementById('restart-btn').addEventListener('click', () => {
    if (state.endless) {
        loadLevel(generateRandomLevel(state.endlessNum), true);
    } else {
        loadLevel(LEVELS[state.levelIndex]);
    }
});

document.getElementById('endless-btn').addEventListener('click', () => {
    state.endlessNum = 1;
    loadLevel(generateRandomLevel(1), true);
});

// ========== 启动 ==========
loadLevel(LEVELS[0]);
window.addEventListener('resize', () => {
    resizeCanvas();
    draw();
});