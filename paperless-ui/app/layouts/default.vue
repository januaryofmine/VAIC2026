<script setup lang="ts">
const { loggedIn, user, clear } = useUserSession();

const initials = computed(() => {
  const s = user.value?.name || user.value?.username || "";
  return s.slice(0, 2).toUpperCase();
});
</script>

<template>
  <div class="min-h-screen bg-[var(--pl-ground)]">
    <header class="topbar">
      <div class="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
        <NuxtLink to="/" class="flex items-center gap-3">
          <div class="brand-mark">P</div>
          <div>
            <div class="text-[15px] font-semibold leading-tight text-white">Paperless</div>
            <div class="text-xs text-[#9fb0cd]">AI for document processing &amp; Meeting preparation</div>
          </div>
        </NuxtLink>
        <div class="flex-1" />

        <ClientOnly>
          <UDropdownMenu
            v-if="loggedIn"
            :items="[[
              { label: user?.name || user?.username || 'Tài khoản', type: 'label' },
              { label: 'Đăng xuất', icon: 'i-lucide-log-out', onSelect: () => clear() },
            ]]"
          >
            <button class="flex items-center gap-2.5 rounded-lg px-1 py-1 hover:bg-white/5">
              <span class="avatar">{{ initials }}</span>
              <span class="hidden text-left leading-tight sm:block">
                <span class="block text-[13.5px] font-semibold text-white">{{ user?.name || user?.username }}</span>
                <span class="block text-[11.5px] text-[#9fb0cd]">{{ user?.username }}</span>
              </span>
            </button>
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
        </ClientOnly>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.topbar {
  background: var(--pl-navy);
  border-bottom: 2px solid var(--pl-gold);
}
.brand-mark {
  width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0;
  background: linear-gradient(150deg, #2a3f6a, #16233f);
  border: 1px solid rgba(201, 162, 39, 0.55);
  display: grid; place-items: center;
  color: var(--pl-gold); font-weight: 700; font-size: 18px;
}
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  background: var(--pl-gold); color: var(--pl-navy-deep);
  display: grid; place-items: center; font-weight: 700; font-size: 13px;
}
</style>
