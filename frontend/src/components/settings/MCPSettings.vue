<template>
  <div class="w-full">
    <div class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('MCP Servers') }}</div>
    <div class="text-xs text-[var(--text-tertiary)] mb-4">
      {{ t('Configure BigModel MCP server API keys. Servers without key will stay disabled.') }}
    </div>

    <div class="space-y-3 mb-4">
      <div
        v-for="server in orderedServers"
        :key="server.server_id"
        class="border border-[var(--border-main)] rounded-lg p-3 bg-[var(--background-menu-white)]"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="text-sm font-medium text-[var(--text-primary)] truncate">{{ server.title }}</div>
            <div class="text-xs text-[var(--text-tertiary)] truncate">{{ server.description }}</div>
          </div>
          <span
            class="text-[11px] px-2 py-1 rounded-full border"
            :class="server.enabled ? 'text-green-700 border-green-300 bg-green-50' : 'text-[var(--text-tertiary)] border-[var(--border-main)]'"
          >
            {{ server.enabled ? t('Enabled') : t('Disabled') }}
          </span>
        </div>
      </div>
    </div>

    <div class="space-y-3">
      <div>
        <label class="text-xs text-[var(--text-tertiary)] mb-1 block">BigModel Vision API Key</label>
        <input v-model="form.vision_api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Enter API Key" />
      </div>
      <div>
        <label class="text-xs text-[var(--text-tertiary)] mb-1 block">BigModel Search API Key</label>
        <input v-model="form.search_api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Enter API Key" />
      </div>
      <div>
        <label class="text-xs text-[var(--text-tertiary)] mb-1 block">BigModel Reader API Key</label>
        <input v-model="form.reader_api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Enter API Key" />
      </div>
      <div>
        <label class="text-xs text-[var(--text-tertiary)] mb-1 block">BigModel ZRead API Key</label>
        <input v-model="form.zread_api_key" type="password" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Enter API Key" />
      </div>
    </div>

    <div class="flex justify-end mt-4">
      <button
        class="px-3 py-1.5 text-sm border rounded bg-[var(--Button-primary-black)] text-[var(--text-onblack)] disabled:opacity-50"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? t('Saving...') : t('Save MCP Settings') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { getMCPSettings, updateMCPSettings, type BigModelMCPServerId, type MCPServerSetting } from '@/api/mcp';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

const { t } = useI18n();

const saving = ref(false);
const serverMap = ref<Record<BigModelMCPServerId, MCPServerSetting> | null>(null);

const form = reactive({
  vision_api_key: '',
  search_api_key: '',
  reader_api_key: '',
  zread_api_key: '',
});

const orderedServerIds: BigModelMCPServerId[] = [
  'bigmodel_vision',
  'bigmodel_search',
  'bigmodel_reader',
  'bigmodel_zread',
];

const orderedServers = computed(() => {
  if (!serverMap.value) return [];
  return orderedServerIds.map(id => serverMap.value![id]).filter(Boolean);
});

const load = async () => {
  try {
    const data = await getMCPSettings();
    serverMap.value = data.servers;
    form.vision_api_key = data.api_keys.vision_api_key || '';
    form.search_api_key = data.api_keys.search_api_key || '';
    form.reader_api_key = data.api_keys.reader_api_key || '';
    form.zread_api_key = data.api_keys.zread_api_key || '';
  } catch (e: any) {
    showErrorToast(e?.message || 'Failed to load MCP settings');
  }
};

const save = async () => {
  saving.value = true;
  try {
    const data = await updateMCPSettings({
      vision_api_key: form.vision_api_key,
      search_api_key: form.search_api_key,
      reader_api_key: form.reader_api_key,
      zread_api_key: form.zread_api_key,
    });
    serverMap.value = data.servers;
    showSuccessToast(t('MCP settings saved'));
  } catch (e: any) {
    showErrorToast(e?.message || 'Failed to save MCP settings');
  } finally {
    saving.value = false;
  }
};

onMounted(load);
</script>
