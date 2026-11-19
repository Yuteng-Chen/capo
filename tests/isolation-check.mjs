import assert from 'node:assert/strict';
import { fork } from 'node:child_process';
import { on, once } from 'node:events';
import { copyFile, link, mkdir, mkdtemp, readFile, realpath, rm, stat, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const timeoutMs = 10_000;

function send(channel, message) {
  return new Promise((resolve, reject) => {
    channel.send(message, error => error ? reject(error) : resolve());
  });
}

async function runWriter(output) {
  const commands = on(process, 'message', {
    close: ['disconnect'],
    signal: AbortSignal.timeout(timeoutMs),
  });
  try {
    await send(process, 'ready');
    for await (const [command] of commands) {
      if (command === 'stop') {
        process.disconnect();
        break;
      }
      assert.equal(command, 'write');
      await writeFile(output, 'late old write');
      await send(process, 'written');
    }
  } finally {
    await commands.return();
    if (process.connected) process.disconnect();
  }
}

async function expectMessage(messages, expected) {
  const { value, done } = await messages.next();
  assert.equal(done, false, `Writer closed before sending ${expected}`);
  assert.equal(value[0], expected);
}

async function checkIsolation() {
  const directory = await mkdtemp(join(tmpdir(), 'router-isolation-'));
  try {
    const oldDir = join(directory, 'old');
    const replacementDir = join(directory, 'replacement');
    const oldFile = join(oldDir, 'artifact.txt');
    const replacementFile = join(replacementDir, 'artifact.txt');
    await mkdir(oldDir);
    await mkdir(replacementDir);
    await writeFile(oldFile, 'baseline');
    await copyFile(oldFile, replacementFile);

    const writer = fork(new URL(import.meta.url), ['--writer', oldFile], {
      env: {},
      execArgv: [],
      stdio: ['ignore', 'ignore', 'inherit', 'ipc'],
    });
    const closed = new Promise(resolve => writer.once('close', resolve));
    const signal = AbortSignal.timeout(timeoutMs);
    const exit = once(writer, 'close', { signal }).catch(error => [null, null, error]);
    const messages = on(writer, 'message', { close: ['close'], signal });
    try {
      await expectMessage(messages, 'ready');
      await writeFile(replacementFile, 'replacement');
      assert.equal(await readFile(oldFile, 'utf8'), 'baseline');
      assert.equal(writer.exitCode, null);
      assert.equal(writer.signalCode, null);
      const original = await stat(oldFile);
      const replacement = await stat(replacementFile);
      assert.notDeepEqual([replacement.dev, replacement.ino], [original.dev, original.ino]);

      await send(writer, 'write');
      await expectMessage(messages, 'written');
      assert.equal(await readFile(oldFile, 'utf8'), 'late old write');
      assert.equal(await readFile(replacementFile, 'utf8'), 'replacement');

      const symlinkAlias = join(replacementDir, 'shared-output');
      const hardlinkAlias = join(replacementDir, 'shared-artifact.txt');
      await symlink(oldDir, symlinkAlias, 'dir');
      await link(oldFile, hardlinkAlias);
      assert.equal(await realpath(symlinkAlias), await realpath(oldDir));
      const linked = await stat(hardlinkAlias);
      assert.deepEqual([linked.dev, linked.ino], [original.dev, original.ino]);

      await send(writer, 'stop');
      const [code, exitSignal, error] = await exit;
      if (error) throw error;
      assert.equal(exitSignal, null);
      assert.equal(code, 0);
      await copyFile(replacementFile, oldFile);
      assert.equal(await readFile(oldFile, 'utf8'), 'replacement');
    } finally {
      if (writer.pid && writer.exitCode === null && writer.signalCode === null) {
        writer.kill('SIGKILL');
      }
      await closed;
      await messages.return();
    }
  } finally {
    await rm(directory, { force: true, recursive: true });
  }
}

try {
  if (process.argv[2] === '--writer' && process.send) {
    await runWriter(process.argv[3]);
  } else {
    await checkIsolation();
    console.log('PASS: distinct files, late write isolation, symlink and hardlink detection, and integration after child exit.');
    console.log('Scope: controlled child-process and filesystem experiment. Host dispatch and enforcement require separate verification.');
  }
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
