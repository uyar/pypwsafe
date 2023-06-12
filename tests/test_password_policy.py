# =============================================================================
# This file is part of PyPWSafe.
#
# PyPWSafe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# PyPWSafe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyPWSafe.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================

# original author: Paulson McIntyre <paul@gpmidi.net>


SAFE_FILENAME = "PasswordPolicyTest.psafe3"

FIXED_POLICIES = {
    "Policy 1": {
        "useLowercase": True,
        "useUppercase": True,
        "useDigits": True,
        "useSymbols": False,
        "useHexDigits": False,
        "useEasyVision": False,
        "makePronounceable": False,
        "minTotalLength": 16,
        "minLowercaseCharCount": 3,
        "minUppercaseCharCount": 2,
        "minDigitCount": 1,
        "minSpecialCharCount": 0,
        "allowedSpecialSymbols": "+-=_@#$%^&;:,.<>/~\\[](){}?!|",
    },
    "Policy Hex": {
        "useLowercase": False,
        "useUppercase": False,
        "useDigits": False,
        "useSymbols": False,
        "useHexDigits": True,
        "useEasyVision": False,
        "makePronounceable": False,
        "minTotalLength": 20,
        "minLowercaseCharCount": 1,
        "minUppercaseCharCount": 1,
        "minDigitCount": 1,
        "minSpecialCharCount": 1,
        "allowedSpecialSymbols": "+-=_@#$%^&;:,.<>/~\\[](){}?!|",
    },
    "Policy Long": {
        "useLowercase": True,
        "useUppercase": True,
        "useDigits": True,
        "useSymbols": True,
        "useHexDigits": False,
        "useEasyVision": True,
        "makePronounceable": False,
        "minTotalLength": 30,
        "minLowercaseCharCount": 1,
        "minUppercaseCharCount": 1,
        "minDigitCount": 1,
        "minSpecialCharCount": 1,
        "allowedSpecialSymbols": "+-=_@#$%^<>/~\\?",
    },
}


def test_policy_flags_should_be_set_correctly(test_safe):
    safe = test_safe(SAFE_FILENAME, "RO")
    for policy in safe.getDbPolicies():
        if policy["name"] in FIXED_POLICIES:
            for k, v in FIXED_POLICIES[policy["name"]].items():
                assert policy[k] == v
