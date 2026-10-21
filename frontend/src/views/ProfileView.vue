<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function onSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await http.put('/users/me/password', {
      old_password: form.old_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码修改成功，请重新登录')
    auth.logout()
    router.push({ name: 'login' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="profile-page">
    <el-card class="profile-card">
      <template #header>
        <span>个人中心 · 修改密码</span>
      </template>
      <p class="profile-tip">当前账号：{{ auth.user?.username }}</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        style="max-width: 420px"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">确认修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  padding: 24px;
}

.profile-card {
  max-width: 560px;
}

.profile-tip {
  color: #909399;
  font-size: 14px;
  margin: 0 0 20px;
}
</style>
