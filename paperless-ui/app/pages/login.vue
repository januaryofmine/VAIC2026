<script setup lang="ts">
definePageMeta({ layout: false });
const route = useRoute();
const { loggedIn, user, clear } = useUserSession();
const hasError = computed(() => route.query.error === "github_oauth_error");
</script>

<template>
  <div class="mx-auto max-w-sm py-12">
    <UCard>
      <template #header>
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-file-text" class="text-xl text-primary" />
          <span class="font-semibold">Paperless Meetings</span>
        </div>
      </template>

      <div v-if="loggedIn" class="flex flex-col items-center gap-3 py-2 text-center">
        <UAvatar :src="user?.avatarUrl ?? undefined" :alt="user?.username" size="lg" />
        <p>Đã đăng nhập với <strong>{{ user?.name || user?.username }}</strong></p>
        <UButton color="neutral" variant="subtle" @click="clear">Đăng xuất</UButton>
        <UButton to="/" variant="link">Về trang chính</UButton>
      </div>

      <div v-else class="flex flex-col gap-4 py-2">
        <p class="text-sm text-[var(--ui-text-muted)]">
          Đăng nhập để lưu tài liệu và lịch sử hỏi đáp của bạn.
        </p>
        <UButton
          to="/api/auth/github"
          icon="i-simple-icons-github"
          label="Đăng nhập với GitHub"
          color="neutral"
          size="lg"
          external
          block
        />
        <UAlert
          v-if="hasError"
          title="Đăng nhập thất bại"
          description="Xác thực GitHub không thành công. Vui lòng thử lại."
          color="error"
          variant="subtle"
          icon="i-lucide-alert-circle"
        />
      </div>
    </UCard>
  </div>
</template>
