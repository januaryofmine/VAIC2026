<script setup lang="ts">
const { loggedIn, user, clear } = useUserSession();
</script>

<template>
  <div class="min-h-screen bg-[var(--ui-bg-muted)]">
    <header class="border-b border-[var(--ui-border)] bg-[var(--ui-bg)]">
      <div class="mx-auto flex max-w-4xl items-center gap-2 px-4 py-3">
        <UIcon name="i-lucide-file-text" class="text-xl text-primary" />
        <NuxtLink to="/" class="font-semibold">Paperless Meetings</NuxtLink>
        <div class="flex-1" />
        <UDropdownMenu
          v-if="loggedIn"
          :items="[[
            { label: user?.name || user?.username || 'Tài khoản', type: 'label' },
            { label: 'Đăng xuất', icon: 'i-lucide-log-out', onSelect: () => clear() },
          ]]"
        >
          <UButton variant="ghost" color="neutral" class="gap-2 px-1">
            <UAvatar :src="user?.avatarUrl ?? undefined" :alt="user?.username" size="xs" />
            <span class="hidden text-sm sm:inline">{{ user?.username }}</span>
          </UButton>
        </UDropdownMenu>
        <UButton
          v-else
          to="/login"
          icon="i-simple-icons-github"
          label="Đăng nhập"
          color="neutral"
          variant="subtle"
          size="sm"
        />
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-4 py-6">
      <slot />
    </main>
  </div>
</template>
