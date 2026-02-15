import { computed, ref } from 'vue';

export type OpsMenuTab = 'chat' | 'task' | 'node';

const activeTab = ref<OpsMenuTab>('chat');
const selectedNodeId = ref<string>('');

export function useOpsMenu() {
  const setActiveTab = (tab: OpsMenuTab) => {
    activeTab.value = tab;
  };

  const setSelectedNodeId = (nodeId: string) => {
    selectedNodeId.value = nodeId;
  };

  return {
    activeTab: computed(() => activeTab.value),
    selectedNodeId: computed(() => selectedNodeId.value),
    setActiveTab,
    setSelectedNodeId,
  };
}
