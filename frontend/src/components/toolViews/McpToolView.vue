<template>
  <div
    class="h-[36px] flex items-center px-3 w-full bg-[var(--background-gray-main)] border-b border-[var(--border-main)] rounded-t-[12px] shadow-[inset_0px_1px_0px_0px_#FFFFFF] dark:shadow-[inset_0px_1px_0px_0px_#FFFFFF30]">
    <div class="flex-1 flex items-center justify-center">
      <div class="max-w-[260px] truncate text-[var(--text-tertiary)] text-sm font-medium text-center">
        {{ t(serverLabel) }}
      </div>
    </div>
  </div>

  <div class="flex-1 min-h-0 w-full overflow-y-auto">
    <div class="flex-1 min-h-0 max-w-[720px] mx-auto px-4 py-3">
      <div class="mb-3 p-3 rounded-lg bg-[var(--fill-tsp-gray-main)]">
        <div class="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1">{{ t('MCP Server') }}</div>
        <div class="text-sm text-[var(--text-primary)] font-medium">{{ t(serverLabel) }}</div>
        <div class="text-xs text-[var(--text-tertiary)] mt-1">{{ t(serverHint) }}</div>
      </div>

      <div class="text-[var(--text-primary)] text-sm font-medium mb-2">
        {{ t('Call') }}: {{ parsed.toolName }}
      </div>

      <div v-if="parsed.serverAlias === 'search'" class="space-y-3">
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Search Query') }}</div>
          <div class="text-sm text-[var(--text-primary)]">{{ searchQuery || '-' }}</div>
        </div>

        <div v-if="parsedResult.links.length > 0" class="space-y-2">
          <div class="text-xs text-[var(--text-tertiary)]">{{ t('Links') }} ({{ parsedResult.links.length }})</div>
          <div v-for="(item, idx) in parsedResult.links" :key="`${item.url}-${idx}`" class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
            <a :href="item.url" target="_blank" class="block text-sm font-medium text-[var(--text-primary)] hover:underline line-clamp-2">{{ item.title || item.url }}</a>
            <div class="text-xs text-[var(--text-tertiary)] mt-1 break-all">{{ item.url }}</div>
            <div v-if="item.snippet" class="text-xs text-[var(--text-secondary)] mt-2 line-clamp-4">{{ item.snippet }}</div>
          </div>
        </div>

        <div v-else class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)] text-xs text-[var(--text-tertiary)]">
          {{ t('No structured search links found in response.') }}
        </div>
      </div>

      <div v-else-if="parsed.serverAlias === 'reader'" class="space-y-3">
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Source URL') }}</div>
          <a v-if="readerUrl" :href="readerUrl" target="_blank" class="text-sm text-[var(--text-primary)] hover:underline break-all">{{ readerUrl }}</a>
          <div v-else class="text-sm text-[var(--text-primary)]">-</div>
        </div>

        <div v-if="parsedResult.title" class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Title') }}</div>
          <div class="text-sm text-[var(--text-primary)]">{{ parsedResult.title }}</div>
          <div v-if="parsedResult.description" class="text-xs text-[var(--text-secondary)] mt-2">{{ parsedResult.description }}</div>
        </div>

        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Extracted Content') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ extractedContent }}</pre>
        </div>
      </div>

      <div v-else-if="parsed.serverAlias === 'zread'" class="space-y-3">
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Repository') }}</div>
          <div class="text-sm text-[var(--text-primary)]">{{ zreadRepo || '-' }}</div>
          <div v-if="zreadTarget" class="text-xs text-[var(--text-secondary)] mt-2">{{ zreadTarget }}</div>
        </div>

        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Result') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ parsedResult.text }}</pre>
        </div>
      </div>

      <div v-else-if="parsed.serverAlias === 'vision'" class="space-y-3">
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Image Input') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ imageInputPreview }}</pre>
        </div>
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Result') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ parsedResult.text }}</pre>
        </div>
      </div>

      <div v-else class="space-y-3">
        <div v-if="toolContent.args && Object.keys(toolContent.args).length > 0" class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Arguments') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ JSON.stringify(toolContent.args, null, 2) }}</pre>
        </div>
        <div class="rounded-lg border border-[var(--border-light)] p-3 bg-[var(--background-menu-white)]">
          <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ t('Result') }}</div>
          <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words">{{ parsedResult.text }}</pre>
        </div>
      </div>

      <div v-if="!toolContent.content?.result" class="text-[var(--text-tertiary)] text-sm mt-3">
        {{ toolContent.status === 'calling' ? t('Tool is executing...') : t('Waiting for result...') }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ToolContent } from '@/types/message';
import { mcpServerLabelKey, parseMCPFunction, parseMCPResult } from '@/utils/mcp';

const { t } = useI18n();

const props = defineProps<{
  sessionId: string;
  toolContent: ToolContent;
  live: boolean;
}>();

const parsed = computed(() => parseMCPFunction(props.toolContent.function));
const parsedResult = computed(() => parseMCPResult(props.toolContent.content?.result));

const serverLabel = computed(() => mcpServerLabelKey(parsed.value.serverAlias));
const serverHint = computed(() => {
  if (parsed.value.serverAlias === 'vision') return 'Send images with requirements and get concrete visual understanding results.';
  if (parsed.value.serverAlias === 'search') return 'Web search MCP optimized for retrieval with lower token cost than browser crawling.';
  if (parsed.value.serverAlias === 'reader') return 'Fetch URL content and return structured, model-friendly text extraction.';
  if (parsed.value.serverAlias === 'zread') return 'Analyze GitHub repositories, file structures, and source code content.';
  return 'No MCP server metadata';
});

const searchQuery = computed(() => props.toolContent.args?.search_query || props.toolContent.args?.query || '');
const readerUrl = computed(() => props.toolContent.args?.url || props.toolContent.args?.link || '');
const zreadRepo = computed(() => props.toolContent.args?.repo_name || props.toolContent.args?.repo || '');
const zreadTarget = computed(() => props.toolContent.args?.file_path || props.toolContent.args?.dir_path || props.toolContent.args?.query || '');

const extractedContent = computed(() => {
  if (parsedResult.value.content) return String(parsedResult.value.content);
  if (typeof parsedResult.value.parsed === 'string') return parsedResult.value.parsed;
  return parsedResult.value.text;
});

const imageInputPreview = computed(() => {
  const args = props.toolContent.args || {};
  const img = args.image || args.image_url || args.image_urls || args.images || args.files;
  if (img === undefined) return JSON.stringify(args, null, 2);
  if (typeof img === 'string') return img;
  return JSON.stringify(img, null, 2);
});
</script>
