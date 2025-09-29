import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import json
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger()

class NotificationType(Enum):
    TRADE_EXECUTED = "trade_executed"
    PRICE_ALERT = "price_alert"
    POSITION_UPDATE = "position_update"
    RISK_WARNING = "risk_warning"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ERROR = "error"

@dataclass
class Notification:
    type: NotificationType
    title: str
    message: str
    data: Dict
    timestamp: datetime
    priority: str = "normal"  # low, normal, high, critical

class EmailNotifier:
    """Email notification service"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = os.getenv("NOTIFICATION_EMAIL", "")
        self.password = os.getenv("NOTIFICATION_EMAIL_PASSWORD", "")
        self.recipient_emails = os.getenv("RECIPIENT_EMAILS", "").split(",")
        
        if not self.email or not self.password:
            logger.warning("Email credentials not configured. Email notifications disabled.")
    
    def send_notification(self, notification: Notification) -> bool:
        """Send email notification"""
        if not self.email or not self.password or not self.recipient_emails:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = ", ".join(self.recipient_emails)
            msg['Subject'] = f"🤖 Trading Bot: {notification.title}"
            
            # Create HTML content
            html_content = self._create_html_content(notification)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _create_html_content(self, notification: Notification) -> str:
        """Create HTML email content"""
        priority_colors = {
            "low": "#28a745",
            "normal": "#007bff",
            "high": "#ffc107",
            "critical": "#dc3545"
        }
        
        color = priority_colors.get(notification.priority, "#007bff")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; color: white; padding: 20px;">
                    <h1 style="margin: 0; font-size: 24px;">{notification.title}</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">{notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div style="padding: 20px;">
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        {notification.message}
                    </p>
                    
                    {self._format_data_table(notification.data)}
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d; text-align: center;">
                        Trading Bot Notification System | Priority: {notification.priority.upper()}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_data_table(self, data: Dict) -> str:
        """Format data as HTML table"""
        if not data:
            return ""
        
        table_html = '<table style="width: 100%; border-collapse: collapse; margin-top: 15px;">'
        
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            
            table_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #dee2e6; background-color: #f8f9fa; font-weight: bold; width: 30%;">
                    {key.replace('_', ' ').title()}
                </td>
                <td style="padding: 8px; border: 1px solid #dee2e6;">
                    {value}
                </td>
            </tr>
            """
        
        table_html += '</table>'
        return table_html

class DiscordNotifier:
    """Discord webhook notification service"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured. Discord notifications disabled.")
    
    def send_notification(self, notification: Notification) -> bool:
        """Send Discord notification"""
        if not self.webhook_url:
            return False
        
        try:
            import requests
            
            # Create Discord embed
            embed = self._create_discord_embed(notification)
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Discord notification sent: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def _create_discord_embed(self, notification: Notification) -> Dict:
        """Create Discord embed"""
        priority_colors = {
            "low": 0x28a745,
            "normal": 0x007bff,
            "high": 0xffc107,
            "critical": 0xdc3545
        }
        
        color = priority_colors.get(notification.priority, 0x007bff)
        
        embed = {
            "title": f"🤖 {notification.title}",
            "description": notification.message,
            "color": color,
            "timestamp": notification.timestamp.isoformat(),
            "footer": {
                "text": f"Trading Bot | Priority: {notification.priority.upper()}"
            }
        }
        
        # Add fields for data
        if notification.data:
            fields = []
            for key, value in notification.data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                
                fields.append({
                    "name": key.replace('_', ' ').title(),
                    "value": f"```{value}```" if len(str(value)) > 50 else str(value),
                    "inline": len(str(value)) < 50
                })
            
            embed["fields"] = fields[:25]  # Discord limit
        
        return embed

class NotificationManager:
    """Central notification management system"""
    
    def __init__(self):
        self.email_notifier = EmailNotifier()
        self.discord_notifier = DiscordNotifier()
        self.enabled_channels = {
            "email": True,
            "discord": True,
            "console": True
        }
        self.notification_filters = {}
        self.custom_handlers = []
    
    def add_custom_handler(self, handler: Callable[[Notification], bool]):
        """Add custom notification handler"""
        self.custom_handlers.append(handler)
    
    def set_channel_enabled(self, channel: str, enabled: bool):
        """Enable/disable notification channel"""
        if channel in self.enabled_channels:
            self.enabled_channels[channel] = enabled
            logger.info(f"Notification channel '{channel}' {'enabled' if enabled else 'disabled'}")
    
    def add_filter(self, notification_type: NotificationType, min_priority: str = "normal"):
        """Add notification filter"""
        self.notification_filters[notification_type] = min_priority
    
    def send_notification(self, notification: Notification) -> Dict[str, bool]:
        """Send notification through all enabled channels"""
        results = {}
        
        # Check filters
        if self._should_filter_notification(notification):
            logger.debug(f"Notification filtered: {notification.title}")
            return results
        
        # Console notification
        if self.enabled_channels.get("console", True):
            results["console"] = self._send_console_notification(notification)
        
        # Email notification
        if self.enabled_channels.get("email", True):
            results["email"] = self.email_notifier.send_notification(notification)
        
        # Discord notification
        if self.enabled_channels.get("discord", True):
            results["discord"] = self.discord_notifier.send_notification(notification)
        
        # Custom handlers
        for i, handler in enumerate(self.custom_handlers):
            try:
                results[f"custom_{i}"] = handler(notification)
            except Exception as e:
                logger.error(f"Error in custom notification handler {i}: {e}")
                results[f"custom_{i}"] = False
        
        return results
    
    def _should_filter_notification(self, notification: Notification) -> bool:
        """Check if notification should be filtered out"""
        if notification.type not in self.notification_filters:
            return False
        
        priority_levels = {"low": 0, "normal": 1, "high": 2, "critical": 3}
        min_priority = self.notification_filters[notification.type]
        
        current_priority = priority_levels.get(notification.priority, 1)
        required_priority = priority_levels.get(min_priority, 1)
        
        return current_priority < required_priority
    
    def _send_console_notification(self, notification: Notification) -> bool:
        """Send console notification"""
        try:
            priority_symbols = {
                "low": "ℹ️",
                "normal": "📢",
                "high": "⚠️",
                "critical": "🚨"
            }
            
            symbol = priority_symbols.get(notification.priority, "📢")
            
            logger.info(f"{symbol} {notification.title}")
            logger.info(f"Message: {notification.message}")
            
            if notification.data:
                logger.info(f"Data: {json.dumps(notification.data, indent=2)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending console notification: {e}")
            return False
    
    # Convenience methods for common notifications
    def notify_trade_executed(self, symbol: str, side: str, quantity: float, price: float, order_id: str):
        """Send trade executed notification"""
        notification = Notification(
            type=NotificationType.TRADE_EXECUTED,
            title=f"Trade Executed: {side} {symbol}",
            message=f"Successfully executed {side} order for {quantity} {symbol} at ${price}",
            data={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_id": order_id,
                "total_value": quantity * price
            },
            timestamp=datetime.now(),
            priority="normal"
        )
        
        return self.send_notification(notification)
    
    def notify_price_alert(self, symbol: str, current_price: float, target_price: float, condition: str):
        """Send price alert notification"""
        notification = Notification(
            type=NotificationType.PRICE_ALERT,
            title=f"Price Alert: {symbol}",
            message=f"{symbol} price {condition} ${target_price}. Current price: ${current_price}",
            data={
                "symbol": symbol,
                "current_price": current_price,
                "target_price": target_price,
                "condition": condition,
                "price_change": current_price - target_price
            },
            timestamp=datetime.now(),
            priority="high"
        )
        
        return self.send_notification(notification)
    
    def notify_risk_warning(self, warning_type: str, message: str, data: Dict):
        """Send risk warning notification"""
        notification = Notification(
            type=NotificationType.RISK_WARNING,
            title=f"Risk Warning: {warning_type}",
            message=message,
            data=data,
            timestamp=datetime.now(),
            priority="critical"
        )
        
        return self.send_notification(notification)
    
    def notify_portfolio_summary(self, balance: float, pnl: float, positions_count: int, 
                                total_value: float):
        """Send portfolio summary notification"""
        pnl_percentage = (pnl / balance * 100) if balance > 0 else 0
        
        notification = Notification(
            type=NotificationType.PORTFOLIO_SUMMARY,
            title="Portfolio Summary",
            message=f"Current portfolio balance: ${balance:.2f} | P&L: ${pnl:.2f} ({pnl_percentage:+.2f}%)",
            data={
                "balance": balance,
                "unrealized_pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "positions_count": positions_count,
                "total_portfolio_value": total_value
            },
            timestamp=datetime.now(),
            priority="normal"
        )
        
        return self.send_notification(notification)
    
    def notify_error(self, error_type: str, error_message: str, details: Dict = None):
        """Send error notification"""
        notification = Notification(
            type=NotificationType.ERROR,
            title=f"Error: {error_type}",
            message=error_message,
            data=details or {},
            timestamp=datetime.now(),
            priority="high"
        )
        
        return self.send_notification(notification)

# Global notification manager instance
notification_manager = NotificationManager()

# Convenience functions
def notify_trade(symbol: str, side: str, quantity: float, price: float, order_id: str):
    """Quick function to notify trade execution"""
    return notification_manager.notify_trade_executed(symbol, side, quantity, price, order_id)

def notify_alert(symbol: str, current_price: float, target_price: float, condition: str):
    """Quick function to notify price alert"""
    return notification_manager.notify_price_alert(symbol, current_price, target_price, condition)

def notify_risk(warning_type: str, message: str, data: Dict = None):
    """Quick function to notify risk warning"""
    return notification_manager.notify_risk_warning(warning_type, message, data or {})

def notify_error(error_type: str, message: str, details: Dict = None):
    """Quick function to notify error"""
    return notification_manager.notify_error(error_type, message, details)

def configure_notifications(email_enabled: bool = True, discord_enabled: bool = True, 
                          console_enabled: bool = True):
    """Configure notification channels"""
    notification_manager.set_channel_enabled("email", email_enabled)
    notification_manager.set_channel_enabled("discord", discord_enabled)
    notification_manager.set_channel_enabled("console", console_enabled)

# Example setup function
def setup_notifications():
    """Setup notifications with filters and custom handlers"""
    
    # Add filters to reduce noise
    notification_manager.add_filter(NotificationType.POSITION_UPDATE, "high")
    notification_manager.add_filter(NotificationType.TRADE_EXECUTED, "normal")
    
    # Add custom handler for critical alerts
    def critical_alert_handler(notification: Notification) -> bool:
        if notification.priority == "critical":
            # Could integrate with Slack, Telegram, SMS, etc.
            logger.critical(f"CRITICAL ALERT: {notification.title} - {notification.message}")
        return True
    
    notification_manager.add_custom_handler(critical_alert_handler)
    
    logger.info("Notification system configured with filters and handlers")