#!/usr/bin/env node
/**
 * Desktop notification hook that shows WHAT Claude Code is asking about.
 *
 * The Notification hook payload only carries a generic `message`
 * ("Claude needs your permission to use Bash"), so this hook reads the tail of
 * the session transcript to recover the actual pending tool call and renders it
 * in the notification body.
 *
 * The notification carries a clickable action that focuses the terminal window
 * running this session (Hyprland). Approval itself still happens in the TUI --
 * a Notification hook cannot decide permissions.
 *
 * Usage (settings.json):
 *   node "$CLAUDE_PROJECT_DIR"/.claude/hooks/desktop-notify-with-request-detail.cjs --kind=permission
 *   node "$CLAUDE_PROJECT_DIR"/.claude/hooks/desktop-notify-with-request-detail.cjs --kind=idle
 */

'use strict';

const fs = require('fs');
const { execFileSync, spawn } = require('child_process');

const BODY_MAX_CHARS = 240;
const TRANSCRIPT_TAIL_BYTES = 256 * 1024;
const PPID_WALK_LIMIT = 20;

const SOUNDS = {
  permission: '/usr/share/sounds/freedesktop/stereo/dialog-warning.oga',
  idle: '/usr/share/sounds/freedesktop/stereo/complete.oga'
};

// paplay --volume is a linear scale where 65536 == 100%. Values above 65536
// amplify past the source level; raise this to make notifications louder.
const SOUND_VOLUME = 98304; // 150%

// ---------------------------------------------------------------- worker mode

/**
 * Detached child: shows the notification, waits for the click, focuses terminal.
 * Runs out-of-band so the hook itself never blocks Claude Code.
 */
function runWorker(payloadJson) {
  const { summary, body, kind, windowAddress } = JSON.parse(payloadJson);

  if (SOUNDS[kind] && fs.existsSync(SOUNDS[kind])) {
    spawn('paplay', ['--volume', String(SOUND_VOLUME), SOUNDS[kind]], {
      stdio: 'ignore',
      detached: true
    }).unref();
  }

  const args = ['-a', 'Claude Code'];
  if (kind === 'permission') args.push('-u', 'critical');
  if (windowAddress) args.push('-A', 'focus=Mở terminal');
  args.push(summary, body);

  let chosen = '';
  try {
    // notify-send with -A implies --wait: it blocks until click or dismiss,
    // then prints the chosen action name on stdout.
    chosen = execFileSync('notify-send', args, { encoding: 'utf8' }).trim();
  } catch {
    return;
  }

  if (chosen === 'focus' && windowAddress) {
    try {
      execFileSync('hyprctl', ['dispatch', 'focuswindow', `address:${windowAddress}`], {
        stdio: 'ignore'
      });
    } catch {
      /* window closed in the meantime */
    }
  }
}

// ------------------------------------------------------------ window lookup

/** Read the parent PID of a process from procfs. */
function parentPid(pid) {
  try {
    const status = fs.readFileSync(`/proc/${pid}/status`, 'utf8');
    const match = status.match(/^PPid:\s*(\d+)$/m);
    return match ? Number(match[1]) : 0;
  } catch {
    return 0;
  }
}

/**
 * Find the Hyprland window hosting this session by walking the process tree
 * upward from this hook until a PID matches a mapped client.
 * @returns {string|null} Hyprland window address, or null when not found.
 */
function findSessionWindowAddress() {
  let clients;
  try {
    clients = JSON.parse(execFileSync('hyprctl', ['clients', '-j'], { encoding: 'utf8' }));
  } catch {
    return null;
  }

  const byPid = new Map(clients.map((client) => [client.pid, client.address]));
  let pid = process.pid;

  for (let depth = 0; depth < PPID_WALK_LIMIT && pid > 1; depth += 1) {
    if (byPid.has(pid)) return byPid.get(pid);
    pid = parentPid(pid);
  }
  return null;
}

// -------------------------------------------------------- transcript reading

/** Read only the tail of the transcript; sessions can grow to many megabytes. */
function readTranscriptTail(transcriptPath) {
  let handle;
  try {
    handle = fs.openSync(transcriptPath, 'r');
    const size = fs.fstatSync(handle).size;
    const length = Math.min(size, TRANSCRIPT_TAIL_BYTES);
    const buffer = Buffer.alloc(length);
    fs.readSync(handle, buffer, 0, length, size - length);
    return buffer.toString('utf8');
  } catch {
    return '';
  } finally {
    if (handle !== undefined) fs.closeSync(handle);
  }
}

/**
 * Recover the most recent tool_use block from the transcript.
 * @returns {{name: string, input: Object}|null}
 */
function findPendingToolUse(transcriptPath) {
  if (!transcriptPath) return null;

  const lines = readTranscriptTail(transcriptPath).split('\n');

  // Walk backwards; the first tool_use found is the one awaiting approval.
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i].trim();
    if (!line.startsWith('{')) continue;

    let entry;
    try {
      entry = JSON.parse(line);
    } catch {
      continue; // partial first line from the tail cut, or non-JSON noise
    }

    const content = entry?.message?.content;
    if (!Array.isArray(content)) continue;

    for (let j = content.length - 1; j >= 0; j -= 1) {
      const block = content[j];
      if (block?.type === 'tool_use' && block.name) {
        return { name: block.name, input: block.input || {} };
      }
    }
  }
  return null;
}

// ------------------------------------------------------------- presentation

/** Collapse whitespace and clamp to a length that dunst renders comfortably. */
function clamp(text) {
  const flat = String(text).replace(/\s+/g, ' ').trim();
  return flat.length > BODY_MAX_CHARS ? `${flat.slice(0, BODY_MAX_CHARS - 1)}…` : flat;
}

/** dunst renders the body as Pango markup, so raw entities must be escaped. */
function escapeMarkup(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Render a one-line human summary of a tool call.
 * @returns {string}
 */
function describeToolCall({ name, input }) {
  switch (name) {
    case 'Bash':
      return clamp(input.command || input.description || '');

    case 'Read':
    case 'Write':
    case 'Edit':
    case 'NotebookEdit':
      return clamp(input.file_path || input.path || '');

    case 'Glob':
    case 'Grep':
      return clamp([input.pattern, input.path].filter(Boolean).join('  in  '));

    case 'WebFetch':
      return clamp(input.url || '');

    case 'WebSearch':
      return clamp(input.query || '');

    case 'Agent':
    case 'Task':
      return clamp(input.description || input.prompt || '');

    case 'Skill':
      return clamp([input.skill, input.args].filter(Boolean).join(' '));

    default: {
      // Unknown tool: surface the first short scalar field rather than nothing.
      const scalar = Object.entries(input).find(
        ([, value]) => typeof value === 'string' && value.length > 0
      );
      return scalar ? clamp(scalar[1]) : '';
    }
  }
}

/**
 * Build the notification summary/body pair for a hook invocation.
 * @returns {{summary: string, body: string}}
 */
function buildNotification(kind, payload) {
  const fallback = clamp(payload.message || '');

  if (kind !== 'permission') {
    return { summary: 'Claude Code — đang chờ bạn', body: escapeMarkup(fallback || 'Phiên đang rảnh.') };
  }

  const toolUse = findPendingToolUse(payload.transcript_path);
  if (!toolUse) {
    return { summary: 'Claude Code — cần duyệt quyền', body: escapeMarkup(fallback) };
  }

  const detail = describeToolCall(toolUse);
  const body = detail
    ? `<b>${escapeMarkup(toolUse.name)}</b>\n${escapeMarkup(detail)}`
    : `<b>${escapeMarkup(toolUse.name)}</b>`;

  return { summary: 'Claude Code — cần duyệt quyền', body };
}

// -------------------------------------------------------------------- main

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function main() {
  const workerArg = process.argv.find((arg) => arg.startsWith('--worker='));
  if (workerArg) {
    runWorker(workerArg.slice('--worker='.length));
    return;
  }

  const kindArg = process.argv.find((arg) => arg.startsWith('--kind='));
  const kind = kindArg ? kindArg.slice('--kind='.length) : 'permission';

  let payload = {};
  try {
    payload = JSON.parse(readStdin() || '{}');
  } catch {
    /* malformed payload still yields a generic notification */
  }

  const { summary, body } = buildNotification(kind, payload);

  // Hand off to a detached worker: notify-send blocks while waiting for the
  // click, and a Notification hook must not stall the session.
  const child = spawn(
    process.execPath,
    [__filename, `--worker=${JSON.stringify({ summary, body, kind, windowAddress: findSessionWindowAddress() })}`],
    { stdio: 'ignore', detached: true }
  );
  child.unref();
}

main();
