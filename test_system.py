#!/usr/bin/env python3
"""
Quick test script for Binance Trading Bot
Tests basic functionality without database dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("🧪 Testing Module Imports...")
    
    try:
        from src.utils.logger import get_logger
        print("✅ Logger import: OK")
        
        from src.binance_client import get_client
        print("✅ Binance Client import: OK")
        
        from src.validators import OrderBase, LimitOrder
        print("✅ Validators import: OK")
        
        from src.risk.manager import RiskManager, RiskConfig
        print("✅ Risk Manager import: OK")
        
        from src.analysis.indicators import TechnicalIndicators
        print("✅ Technical Analysis import: OK")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without API calls"""
    print("\n🔧 Testing Basic Functionality...")
    
    try:
        # Test logger
        from src.utils.logger import get_logger
        logger = get_logger()
        logger.info("Test log message")
        print("✅ Logging: OK")
        
        # Test risk config
        from src.risk.manager import RiskConfig
        config = RiskConfig()
        print(f"✅ Risk Config: {config.max_risk_per_trade}% max risk per trade")
        
        # Test validators
        from src.validators import LimitOrder
        order = LimitOrder(symbol="BTCUSDT", side="BUY", qty=0.001, price=50000.0)
        print("✅ Order validation: OK")
        
        print("✅ Basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Functionality error: {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 Binance Trading Bot - System Test")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test functionality
    if imports_ok:
        functionality_ok = test_basic_functionality()
    else:
        functionality_ok = False
    
    print("\n" + "=" * 50)
    if imports_ok and functionality_ok:
        print("🎉 ALL TESTS PASSED! Project is ready for GitHub!")
        print("\n📋 Next Steps:")
        print("1. Copy .env.example to .env and add your API keys")
        print("2. Run: python -m src.main --help")
        print("3. Start with: python -m src.main ping")
        return 0
    else:
        print("❌ Some tests failed. Please fix issues before pushing to GitHub.")
        return 1

if __name__ == "__main__":
    sys.exit(main())