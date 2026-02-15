<template>
  <div :class="isLeftPanelShow ?
    'h-full flex flex-col' :
    'h-full flex flex-col fixed top-0 start-0 bottom-0 z-[1]'" :style="isLeftPanelShow ?
      'width: 300px; transition: width 0.28s cubic-bezier(0.4, 0, 0.2, 1);' :
      'width: 24px; transition: width 0.36s cubic-bezier(0.4, 0, 0.2, 1);'">
    <div
      :class="isLeftPanelShow ?
        'ops-panel ops-slide-up flex flex-col overflow-hidden bg-[var(--background-nav)] h-full opacity-100 translate-x-0 border-r border-[var(--border-main)]' :
        'ops-panel ops-slide-up flex flex-col overflow-hidden bg-[var(--background-nav)] fixed top-1 start-1 bottom-1 z-[1] border-1 dark:border-[1px] border-[var(--border-main)] dark:border-[var(--border-light)] rounded-xl shadow-[0px_8px_32px_0px_rgba(0,0,0,0.16),0px_0px_0px_1px_rgba(0,0,0,0.06)] opacity-0 pointer-events-none -translate-x-10'"
      :style="(isLeftPanelShow ? 'width: 300px;' : 'width: 0px;') + ' transition: opacity 0.2s, transform 0.2s, width 0.2s;'">
      <div class="px-3 pt-3 pb-1">
        <div class="rounded-xl border border-[var(--border-main)] px-3 py-2 bg-[var(--background-card)]/70">
          <div class="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Ops Console</div>
          <div class="text-sm font-semibold text-[var(--text-primary)] mt-0.5">服务器运维控制台</div>
        </div>
      </div>

      <div class="px-3 py-2 mb-2 flex items-center gap-2">
        <button
          class="flex h-8 w-8 shrink-0 items-center justify-center cursor-pointer hover:bg-[var(--fill-tsp-gray-main)] rounded-md border border-transparent hover:border-[var(--border-main)]"
          @click="toggleLeftPanel">
          <PanelLeft class="h-5 w-5 text-[var(--icon-secondary)]" />
        </button>
        <div class="flex items-center gap-1 flex-1 min-w-0">
          <button v-for="menu in menus" :key="menu.key" @click="switchMenu(menu.key)"
            class="flex-1 h-8 rounded-lg text-sm border"
            :class="activeTab === menu.key ? 'bg-[var(--fill-tsp-primary)] border-[var(--border-main)] text-[var(--text-primary)]' : 'bg-transparent border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--fill-tsp-gray-main)]'">
            {{ menu.label }}
          </button>
        </div>
      </div>

      <div class="px-3 mb-1 flex justify-center flex-shrink-0">
        <button @click="handlePrimaryAction"
          class="ops-elevated flex min-w-[36px] w-full items-center justify-center gap-1.5 rounded-lg h-[36px] bg-[var(--Button-primary-white)] hover:bg-white/20 dark:hover:bg-black/60 cursor-pointer shadow-[0px_0.5px_3px_0px_var(--shadow-S)]">
          <Plus class="h-4 w-4 text-[var(--icon-primary)]" />
          <span class="text-sm font-medium text-[var(--text-primary)] whitespace-nowrap truncate">
            {{ primaryActionLabel }}
          </span>
          <div v-if="activeTab !== 'node'" class="flex items-center gap-0.5">
            <span
              class="flex text-[var(--text-tertiary)] justify-center items-center min-w-5 h-5 px-1 rounded-[4px] bg-[var(--fill-tsp-white-light)] border border-[var(--border-light)]">
              <Command :size="14" />
            </span>
            <span
              class="flex justify-center items-center w-5 h-5 px-1 rounded-[4px] bg-[var(--fill-tsp-white-light)] border border-[var(--border-light)] text-sm font-normal text-[var(--text-tertiary)] ">
              K
            </span>
          </div>
        </button>
      </div>

      <div v-if="activeTab === 'node'" class="flex flex-col flex-1 min-h-0 overflow-auto pt-2 pb-5 overflow-x-hidden">
        <button v-for="node in nodes" :key="node.node_id" @click="openNode(node.node_id)"
          class="mx-3 mb-2 rounded-xl border p-3 text-left transition"
          :class="isNodeActive(node.node_id) ? 'bg-[var(--background-white-main)] border-[var(--border-main)] shadow-[0_8px_20px_var(--shadow-XS)]' : 'hover:bg-[var(--fill-tsp-gray-main)] border-transparent'">
          <div class="flex items-center justify-between">
            <div class="text-sm font-semibold truncate text-[var(--text-primary)]">{{ node.name }}</div>
            <span class="text-[10px] px-2 py-0.5 rounded-full"
              :class="node.ssh_enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-100 text-zinc-500'">
              {{ node.ssh_enabled ? 'SSH ON' : 'SSH OFF' }}
            </span>
          </div>
          <div class="text-xs text-[var(--text-tertiary)] truncate mt-1">
            {{ node.description || node.remarks || '暂无描述' }}
          </div>
        </button>
        <div v-if="nodes.length === 0" class="flex-1 flex items-center justify-center text-sm text-[var(--text-tertiary)] px-5 text-center">
          还没有可用节点，点击上方“添加节点”创建。
        </div>
      </div>

      <div v-else-if="displaySessions.length > 0" class="flex flex-col flex-1 min-h-0 overflow-auto pt-2 pb-5 overflow-x-hidden">
        <SessionItem v-for="session in displaySessions" :key="session.session_id" :session="session"
          @deleted="handleSessionDeleted" />
      </div>
      <div v-else class="flex flex-1 flex-col items-center justify-center gap-4">
        <div class="flex flex-col items-center gap-2 text-[var(--text-tertiary)]">
          <MessageSquareDashed :size="38" />
          <span class="text-sm font-medium">{{ emptyHint }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PanelLeft, Plus, Command, MessageSquareDashed } from 'lucide-vue-next';
import SessionItem from './SessionItem.vue';
import { useLeftPanel } from '../composables/useLeftPanel';
import { getSessionsSSE, getSessions } from '../api/agent';
import { listServerNodes, type ServerNode } from '@/api/node';
import { ListSessionItem, SessionStatus } from '../types/response';
import { useI18n } from 'vue-i18n';
import { useOpsMenu, type OpsMenuTab } from '@/composables/useOpsMenu';
import { useSettingsDialog } from '@/composables/useSettingsDialog';

const { t } = useI18n();
const { isLeftPanelShow, toggleLeftPanel } = useLeftPanel();
const route = useRoute();
const router = useRouter();
const { activeTab, setActiveTab } = useOpsMenu();
const { openSettingsDialog } = useSettingsDialog();

const sessions = ref<ListSessionItem[]>([]);
const nodes = ref<ServerNode[]>([]);
const cancelGetSessionsSSE = ref<(() => void) | null>(null);
const nodeRefreshTimer = ref<number | null>(null);

const menus: { key: OpsMenuTab; label: string }[] = [
  { key: 'chat', label: '对话' },
  { key: 'task', label: '任务' },
  { key: 'node', label: '节点' },
];

const displaySessions = computed(() => {
  if (activeTab.value === 'chat') return sessions.value;
  return [...sessions.value].sort((a, b) => {
    const aRunning = a.status === SessionStatus.RUNNING || a.status === SessionStatus.PENDING;
    const bRunning = b.status === SessionStatus.RUNNING || b.status === SessionStatus.PENDING;
    if (aRunning === bRunning) return b.created_at - a.created_at;
    return aRunning ? -1 : 1;
  });
});

const primaryActionLabel = computed(() => {
  if (activeTab.value === 'node') return '添加节点';
  return t('New Task');
});

const emptyHint = computed(() => {
  if (activeTab.value === 'task') return '暂无任务记录';
  return t('Create a task to get started');
});

const isNodeActive = (nodeId: string) => route.path === `/chat/nodes/${nodeId}`;

const updateSessions = async () => {
  try {
    const response = await getSessions();
    sessions.value = response.sessions;
  } catch (error) {
    console.error('Failed to fetch sessions:', error);
  }
};

const fetchSessions = async () => {
  try {
    if (cancelGetSessionsSSE.value) {
      cancelGetSessionsSSE.value();
      cancelGetSessionsSSE.value = null;
    }
    cancelGetSessionsSSE.value = await getSessionsSSE({
      onMessage: (event) => {
        sessions.value = event.data.sessions;
      },
      onError: (error) => {
        console.error('Failed to fetch sessions:', error);
      },
    });
  } catch (error) {
    console.error('Failed to fetch sessions:', error);
  }
};

const loadNodes = async () => {
  try {
    nodes.value = await listServerNodes();
  } catch (error) {
    console.error('Failed to fetch nodes:', error);
  }
};

const handlePrimaryAction = () => {
  if (activeTab.value === 'node') {
    openSettingsDialog('nodes');
    return;
  }
  router.push('/');
};

const switchMenu = (menu: OpsMenuTab) => {
  setActiveTab(menu);
  if (menu === 'node') {
    if (!route.path.startsWith('/chat/nodes')) {
      router.push('/chat/nodes');
    }
    return;
  }
  if (route.path.startsWith('/chat/nodes')) {
    router.push('/chat');
  }
};

const openNode = (nodeId: string) => {
  setActiveTab('node');
  router.push(`/chat/nodes/${nodeId}`);
};

const handleSessionDeleted = (sessionId: string) => {
  sessions.value = sessions.value.filter((session) => session.session_id !== sessionId);
};

const handleKeydown = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault();
    if (activeTab.value !== 'node') {
      router.push('/');
    }
  }
};

watch(() => route.path, async (path) => {
  if (path.startsWith('/chat/nodes')) {
    setActiveTab('node');
    await loadNodes();
  } else if (activeTab.value === 'node') {
    setActiveTab('chat');
  }
  await updateSessions();
});

onMounted(async () => {
  fetchSessions();
  loadNodes();
  nodeRefreshTimer.value = window.setInterval(loadNodes, 20000);
  window.addEventListener('keydown', handleKeydown);
  if (route.path.startsWith('/chat/nodes')) {
    setActiveTab('node');
  }
});

onUnmounted(() => {
  if (cancelGetSessionsSSE.value) {
    cancelGetSessionsSSE.value();
    cancelGetSessionsSSE.value = null;
  }
  if (nodeRefreshTimer.value !== null) {
    window.clearInterval(nodeRefreshTimer.value);
    nodeRefreshTimer.value = null;
  }
  window.removeEventListener('keydown', handleKeydown);
});
</script>
