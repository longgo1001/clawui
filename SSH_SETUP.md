# SSH Key Setup for GitHub (快速完成)

## 公钥 (已生成)
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK0F4+FJkgKOw4lgXDyhjniYHKhnHxDHxIou1ESZa2Pu longgo1001@gmail.com
```

## 手动步骤 (2分钟)

1. 确保浏览器打开 https://github.com/settings/keys
2. 点击 **New SSH key**
3. 标题：`clawui-laptop` (任意)
4. Key 类型：**Authentication** (默认)
5. 内容：粘贴上面的公钥
6. 点击 **Add SSH key**

完成！

## 验证

```bash
ssh -T git@github.com
# 应看到: "Hi longgo1001! You've successfully authenticated..."
```

## 后续

- 我会自动检测并切换 remote 到 SSH
- 然后推送本地提交