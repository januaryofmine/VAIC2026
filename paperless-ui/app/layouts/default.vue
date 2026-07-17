<template>
  <div class="min-h-screen bg-[var(--ui-bg-muted)]">
    <header class="border-b border-[var(--ui-border)] bg-[var(--ui-bg)]">
      <div class="mx-auto flex max-w-4xl items-center gap-2 px-4 py-3">
        <UIcon name="i-lucide-file-text" class="text-xl text-primary" />
        <NuxtLink to="/" class="font-semibold">Paperless Meetings</NuxtLink>
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-4 py-6">
      <slot />
    </main>
  </div>
</template>
