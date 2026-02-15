<template>
  <div v-if="open" class="fixed bg-[var(--background-gray-main)] z-[90] transition-all w-full h-full inset-0">
    <div class="w-full h-full flex flex-col">
      <div class="h-12 px-4 border-b border-[var(--border-main)] bg-[var(--background-gray-main)] flex items-center justify-between">
        <div class="text-sm font-medium text-[var(--text-primary)] truncate">
          {{ `SSH Takeover · ${nodeName || nodeId || 'Unknown Node'}` }}
        </div>
        <button
          @click="close"
          class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors hover:opacity-90 active:opacity-80 bg-[var(--Button-primary-black)] text-[var(--text-onblack)] h-[32px] px-[10px] gap-[6px] text-xs rounded-full border border-[var(--border-dark)]"
        >
          Exit SSH
        </button>
      </div>

      <div
        ref="terminalBody"
        class="flex-1 overflow-auto px-4 py-3 font-mono text-[13px] leading-6 bg-[#0d1117] text-[#e6edf3]"
      >
        <div class="text-[#8b949e] mb-3">Connected. Streaming AI and takeover commands.</div>
        <template v-for="item in records" :key="item.id">
          <div>
            <span class="text-[#7ee787]">{{ prompt(item) }}</span>
            <span> {{ item.command }}</span>
          </div>
          <pre class="whitespace-pre-wrap break-all mb-2">{{ item.output || (item.status === 'pending' ? '...' : '(empty output)') }}</pre>
        </template>
        <div v-if="!records.length" class="text-[#8b949e]">Waiting for SSH command...</div>
      </div>

      <div class="border-t border-[var(--border-main)] bg-[var(--background-gray-main)] px-4 py-3">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-[var(--text-tertiary)]">Manual takeover command</span>
          <label class="text-xs text-[var(--text-tertiary)] inline-flex items-center gap-1">
            <input type="checkbox" v-model="syncToAi" /> Sync to AI context
          </label>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model="command"
            @keydown.enter.prevent="run"
            class="flex-1 rounded-md border border-[var(--border-main)] bg-[var(--background-menu-white)] px-3 py-2 font-mono text-sm"
            placeholder="Type command and press Enter"
          />
          <button
            @click="run"
            :disabled="running || !command.trim()"
            class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors hover:opacity-90 active:opacity-80 bg-[var(--Button-primary-black)] text-[var(--text-onblack)] h-[36px] px-[12px] gap-[6px] text-sm rounded-lg disabled:opacity-50"
          >
            {{ running ? 'Running...' : 'Run' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { execNodeSSH } from '@/api/node';
import { showErrorToast } from '@/utils/toast';
import { nextTick, ref, watch } from 'vue';

export interface SshConsoleRecord {
  id: string;
  source: 'assistant' | 'user';
  command: string;
  output: string;
  status: 'pending' | 'done' | 'failed';
}

const props = defineProps<{
  open: boolean;
  sessionId?: string;
  nodeId?: string;
  nodeName?: string;
  records: SshConsoleRecord[];
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'append-record', record: SshConsoleRecord): void;
}>();

const command = ref('');
const running = ref(false);
const syncToAi = ref(true);
const terminalBody = ref<HTMLElement | null>(null);

const scrollBottom = async () => {
  await nextTick();
  if (terminalBody.value) {
    terminalBody.value.scrollTop = terminalBody.value.scrollHeight;
  }
};

watch(() => props.records.length, scrollBottom);
watch(() => props.open, (v) => v && scrollBottom());

const close = () => emit('close');

const prompt = (item: SshConsoleRecord) =>
  item.source === 'assistant' ? 'manus@remote:~$' : 'user@remote:~$';

const run = async () => {
  if (!props.nodeId || !props.sessionId || !command.value.trim() || running.value) return;
  const cmd = command.value.trim();
  const localId = `user-${Date.now()}`;

  emit('append-record', {
    id: localId,
    source: 'user',
    command: cmd,
    output: '',
    status: 'pending',
  });

  try {
    running.value = true;
    const result = await execNodeSSH(props.nodeId, cmd, undefined, syncToAi.value, props.sessionId);
    emit('append-record', {
      id: localId,
      source: 'user',
      command: cmd,
      output: result.output,
      status: result.success ? 'done' : 'failed',
    });
    command.value = '';
  } catch (e: any) {
    emit('append-record', {
      id: localId,
      source: 'user',
      command: cmd,
      output: e?.response?.data?.msg || 'Takeover command failed',
      status: 'failed',
    });
    showErrorToast(e?.response?.data?.msg || 'Takeover command failed');
  } finally {
    running.value = false;
  }
};
</script>
