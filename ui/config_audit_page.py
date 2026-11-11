"""Security configuration audit placeholder."""

from ui.placeholder import PlaceholderPage


class ConfigAuditPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "安全配置检查",
            "针对明确授权的远程目标进行非破坏性 HTTPS 与安全响应头检查。",
            [
                "授权有效期与资产精确匹配的后端复核",
                "HTTPS 证书、协议与安全响应头只读检查",
                "不跟随未授权重定向、不携带攻击载荷",
                "每次检查先展示目标、方式和授权状态",
            ],
            security_note="当前阶段不发起任何真实网络检测；后续实现默认拒绝、DNS/IP 复核并全程记录审计日志。",
        )
