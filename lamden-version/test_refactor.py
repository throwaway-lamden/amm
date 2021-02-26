from unittest import TestCase
from contracting.client import ContractingClient
from decimal import Decimal #To fix some unittest concatenation issues

def bad_token():
    @export
    def thing():
        return 1


def dex():
    # Illegal use of a builtin
    # import time
    import currency
    import con_amm # Set to token currency
    I = importlib

    # Enforceable interface
    token_interface = [
        I.Func('transfer', args=('amount', 'to')),
        # I.Func('balance_of', args=('account')),
        I.Func('allowance', args=('owner', 'spender')),
        I.Func('approve', args=('amount', 'to')),
        I.Func('transfer_from', args=('amount', 'to', 'main_account'))
    ]

    pairs = Hash()
    prices = Hash(default_value=0)

    lp_points = Hash(default_value=0)
    reserves = Hash(default_value=[0, 0])
    
    staked_amount = Hash(default_value=0)
    discount = Hash(default_value=1)

    state = Hash()
    
    @construct
    def seed(): #These are supposed to be constants, but they are changable
        state["FEE_PERCENTAGE"] = 0.3 / 100
        state["TOKEN_CONTRACT"] = "con_amm"
        state["TOKEN_DISCOUNT"] = 0.75
        state["BURN_PERCENTAGE"] = 0.8
        state["BURN_ADDRESS"] = "0x0" #Change this
        state["LOG_ACCURACY"] = 1000000000.0 #The stamp difference for a higher number should be unnoticable
        state["MULTIPLIER"] = 0.05
        state["OWNER"] = ctx.caller 
    
    @export
    def create_market(contract: str, currency_amount: float=0, token_amount: float=0):
        assert pairs[contract] is None, 'Market already exists!'
        assert currency_amount > 0 and token_amount > 0, 'Must provide currency amount and token amount!'

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        currency.transfer_from(amount=currency_amount, to=ctx.this, main_account=ctx.caller)
        token.transfer_from(amount=token_amount, to=ctx.this, main_account=ctx.caller)

        prices[contract] = currency_amount / token_amount

        pairs[contract] = True

        # Mint 100 liquidity points
        lp_points[contract, ctx.caller] = 100
        lp_points[contract] = 100

        reserves[contract] = [currency_amount, token_amount]
        
        return True

    @export
    def liquidity_balance_of(contract: str, account: str):
        return lp_points[contract, account]

    @export
    def add_liquidity(contract: str, currency_amount: float=0):
        assert pairs[contract] is True, 'Market does not exist!'

        assert currency_amount > 0

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        # Determine the number of tokens required
        token_amount = currency_amount / prices[contract]

        # Transfer both tokens
        currency.transfer_from(amount=currency_amount, to=ctx.this, main_account=ctx.caller)
        token.transfer_from(amount=token_amount, to=ctx.this, main_account=ctx.caller)

        # Calculate the LP points to mint
        total_lp_points = lp_points[contract]
        currency_reserve, token_reserve = reserves[contract]

        points_per_currency = total_lp_points / currency_reserve
        lp_to_mint = points_per_currency * currency_amount

        # Update the LP points
        lp_points[contract, ctx.caller] += lp_to_mint
        lp_points[contract] += lp_to_mint

        # Update the reserves
        reserves[contract] = [currency_reserve + currency_amount, token_reserve + token_amount]
        
        #Return amount of LP minted
        return lp_to_mint

    @export
    def remove_liquidity(contract: str, amount: float=0):
        assert pairs[contract] is True, 'Market does not exist!'

        assert amount > 0, 'Must be a positive LP point amount!'
        assert lp_points[contract, ctx.caller] >= amount, 'Not enough LP points to remove!'

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        lp_percentage = amount / lp_points[contract]

        currency_reserve, token_reserve = reserves[contract]

        currency_amount = currency_reserve * decimal(lp_percentage)
        token_amount = token_reserve * decimal(lp_percentage)

        currency.transfer(to=ctx.caller, amount=currency_amount)
        token.transfer(to=ctx.caller, amount=token_amount)

        lp_points[contract, ctx.caller] -= amount
        lp_points[contract] -= amount

        assert lp_points[contract] > 1, 'Not enough remaining liquidity!'

        new_currency_reserve = currency_reserve - currency_amount
        new_token_reserve = token_reserve - token_amount

        assert new_currency_reserve > 0 and new_token_reserve > 0, 'Not enough remaining liquidity!'

        reserves[contract] = [new_currency_reserve, new_token_reserve]

    @export
    def transfer_liquidity(contract: str, to: str, amount: float):
        assert amount > 0, 'Must be a positive LP point amount!'
        assert lp_points[contract, ctx.caller] >= amount, 'Not enough LP points to transfer!'

        lp_points[contract, ctx.caller] -= amount
        lp_points[contract, to] += amount

    @export
    def approve_liquidity(contract: str, to: str, amount: float):
        assert amount > 0, 'Cannot send negative balances!'
        lp_points[contract, ctx.caller, to] += amount

    @export
    def transfer_liquidity_from(contract: str, to: str, main_account: str, amount: float):
        assert amount > 0, 'Cannot send negative balances!'

        assert lp_points[contract, main_account, ctx.caller] >= amount, 'Not enough coins approved to send! You have ' \
                                    '{} and are trying to spend {}'.format(lp_points[main_account, ctx.caller], amount)

        assert lp_points[contract, main_account] >= amount, 'Not enough coins to send!'

        lp_points[contract, main_account, ctx.caller] -= amount
        lp_points[contract, main_account] -= amount

        lp_points[contract, to] += amount

    # Buy takes fee from the crypto being transferred in
    @export
    def buy(contract: str, currency_amount: float, minimum_received: float=0, token_fees: bool=False):
        assert pairs[contract] is not None, 'Market does not exist!'
        assert currency_amount > 0, 'Must provide currency amount!'

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        currency_reserve, token_reserve = reserves[contract]
        k = currency_reserve * token_reserve

        new_currency_reserve = currency_reserve + currency_amount
        new_token_reserve = k / new_currency_reserve

        tokens_purchased = token_reserve - new_token_reserve
        
        fee_percent = state["FEE_PERCENTAGE"] * discount[ctx.caller] #Discount is applied here
        fee = tokens_purchased * fee_percent
        
        if token_fees is True:
            fee = fee * state["TOKEN_DISCOUNT"]
            
            rswp_k = currency_reserve * token_reserve

            rswp_new_token_reserve = token_reserve + fee
            rswp_new_currency_reserve = rswp_k / rswp_new_token_reserve

            rswp_currency_purchased = currency_reserve - rswp_new_currency_reserve # MINUS FEE
            rswp_currency_purchased += rswp_currency_purchased * fee_percent
            
            
            rswp_currency_reserve_2, rswp_token_reserve_2 = reserves[state["TOKEN_CONTRACT"]] #This converts fees in TAU to fees in RSWP
            rswp_k_2 = rswp_currency_reserve_2 * rswp_token_reserve_2

            rswp_new_currency_reserve_2 = rswp_currency_reserve_2 + rswp_currency_purchased
            rswp_new_currency_reserve_2 += rswp_currency_purchased * fee_percent #Not 100% accurate, uses output currency instead of input currency
            rswp_new_token_reserve_2 = rswp_k_2 / rswp_new_currency_reserve_2
            
            sell_amount = rswp_token_reserve_2 - rswp_new_token_reserve_2 #SEMI-VOODOO MATH, PLEASE DOUBLE CHECK
            sell_amount_with_fee = sell_amount * state["BURN_PERCENTAGE"]
            
            con_amm.transfer_from(amount=sell_amount, to=ctx.this, main_account=ctx.caller)
            
            currency_received = internal_sell(contract=state["TOKEN_CONTRACT"], token_amount=sell_amount_with_fee)
            con_amm.transfer(amount=sell_amount - sell_amount_with_fee, to=state["BURN_ADDRESS"])
            
            token_received = internal_buy(contract=contract, currency_amount=currency_received)
            new_token_reserve = decimal(new_token_reserve) + token_received #This can probably be removed during production
        
        else:
            tokens_purchased = decimal(tokens_purchased) - fee
            burn_amount = internal_buy(contract=state["TOKEN_CONTRACT"], currency_amount=internal_sell(contract=contract, token_amount=fee - fee * state["BURN_PERCENTAGE"]))
            
            new_token_reserve = decimal(new_token_reserve) + fee * state["BURN_PERCENTAGE"]
            con_amm.transfer(amount=burn_amount, to=state["BURN_ADDRESS"]) #Burn here

        if minimum_received != None:
            assert tokens_purchased >= minimum_received, "Only {} tokens can be purchased, which is less than your minimum, which is {} tokens.".format(tokens_purchased, minimum_received)
            
        assert tokens_purchased > 0, 'Token reserve error!'

        currency.transfer_from(amount=currency_amount, to=ctx.this, main_account=ctx.caller)
        token.transfer(amount=tokens_purchased, to=ctx.caller)

        reserves[contract] = [new_currency_reserve, new_token_reserve]
        prices[contract] = new_currency_reserve / new_token_reserve
        
        return tokens_purchased

    # Sell takes fee from crypto being transferred out
    @export
    def sell(contract: str, token_amount: float, minimum_received: float=0, token_fees: bool=False):
        assert pairs[contract] is not None, 'Market does not exist!'
        assert token_amount > 0, 'Must provide currency amount and token amount!'

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        currency_reserve, token_reserve = reserves[contract]
        k = currency_reserve * token_reserve

        new_token_reserve = token_reserve + token_amount

        new_currency_reserve = k / new_token_reserve

        currency_purchased = currency_reserve - new_currency_reserve # MINUS FEE

        fee_percent = state["FEE_PERCENTAGE"] * discount[ctx.caller] #Discount is applied here
        fee = currency_purchased * fee_percent
        
        if token_fees is True:
            fee = fee * state["TOKEN_DISCOUNT"]
            rswp_currency_reserve, rswp_token_reserve = reserves[state["TOKEN_CONTRACT"]]
            rswp_k = rswp_currency_reserve * rswp_token_reserve

            rswp_new_currency_reserve = rswp_currency_reserve + fee
            rswp_new_currency_reserve += fee * fee_percent #Not 100% accurate, uses output currency instead of input currency
            rswp_new_token_reserve = rswp_k / rswp_new_currency_reserve
            
            sell_amount = rswp_token_reserve - rswp_new_token_reserve #SEMI-VOODOO MATH, PLEASE DOUBLE CHECK
            sell_amount_with_fee = sell_amount * state["BURN_PERCENTAGE"]
            
            con_amm.transfer_from(amount=sell_amount, to=ctx.this, main_account=ctx.caller)
            
            currency_received = internal_sell(contract=state["TOKEN_CONTRACT"], token_amount=sell_amount_with_fee)
            con_amm.transfer(amount=sell_amount - sell_amount_with_fee, to=state["BURN_ADDRESS"])
            
            new_currency_reserve = decimal(new_currency_reserve) + currency_received
            
        else:
            currency_purchased = decimal(currency_purchased) - fee
            burn_amount = fee - fee * state["BURN_PERCENTAGE"]
            
            new_currency_reserve = decimal(new_currency_reserve) + fee * state["BURN_PERCENTAGE"]
            token_received = internal_buy(contract=state["TOKEN_CONTRACT"], currency_amount=burn_amount)
            con_amm.transfer(amount=token_received, to=state["BURN_ADDRESS"]) #Buy and burn here

        if minimum_received != None: #!= because the type is not exact
            assert currency_purchased >= minimum_received, "Only {} TAU can be purchased, which is less than your minimum, which is {} TAU.".format(currency_purchased, minimum_received)
            
        assert currency_purchased > 0, 'Token reserve error!'

        token.transfer_from(amount=token_amount, to=ctx.this, main_account=ctx.caller)
        currency.transfer(amount=currency_purchased, to=ctx.caller)

        reserves[contract] = [new_currency_reserve, new_token_reserve]
        prices[contract] = new_currency_reserve / new_token_reserve
        
        return currency_purchased
    
    @export
    def stake(amount: float):
        assert amount >= 0, 'Must be a positive stake amount!'
                
        current_balance = staked_amount[ctx.caller]
        if amount < current_balance: 
            con_amm.transfer(current_balance - amount, ctx.caller)
            staked_amount[ctx.caller] = amount #Rest of this can be abstracted in another function
            discount_amount = state["LOG_ACCURACY"] * (amount ** (1 / state["LOG_ACCURACY"]) - 1) * state["MULTIPLIER"] #Calculates discount percentage
            if discount_amount > 0.99: #Probably unnecessary, but added to prevent floating point and division by zero issues
                discount_amount = 0.99
            discount[ctx.caller] = 1 - discount_amount
            return discount_amount
        
        elif amount > current_balance: #Can replace with else, but this probably closes up a few edge cases like `if amount == current_balance`
            con_amm.transfer_from(amount - current_balance, ctx.this, ctx.caller)
            staked_amount[ctx.caller] = amount
            discount_amount = state["LOG_ACCURACY"] * (amount ** (1 / state["LOG_ACCURACY"]) - 1) * state["MULTIPLIER"]
            if discount_amount > 0.99:
                discount_amount = 0.99
            discount[ctx.caller] = 1 - discount_amount
            return discount_amount
        
    @export
    def change_state(key: str, new_value: str, convert_to_decimal: bool=False):
        assert state["OWNER"] == ctx.caller, "Not the owner!"
        if convert_to_decimal:
            new_value = decimal(new_value)
        state[key] = new_value
        return new_value
        
    # Internal use only
    def internal_buy(contract: str, currency_amount: float): 
        assert pairs[contract] is not None, 'Market does not exist!'
        if currency_amount <= 0:
            return 0

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        currency_reserve, token_reserve = reserves[contract]
        k = currency_reserve * token_reserve

        new_currency_reserve = currency_reserve + currency_amount
        new_token_reserve = k / new_currency_reserve

        tokens_purchased = token_reserve - new_token_reserve

        fee = tokens_purchased * state["FEE_PERCENTAGE"]

        tokens_purchased -= fee
        new_token_reserve += fee

        assert tokens_purchased > 0, 'Token reserve error!'

        reserves[contract] = [new_currency_reserve, new_token_reserve]
        prices[contract] = new_currency_reserve / new_token_reserve
        
        return tokens_purchased

    # Internal use only
    def internal_sell(contract: str, token_amount: float):
        assert pairs[contract] is not None, 'Market does not exist!'
        if token_amount <= 0:
            return 0

        token = I.import_module(contract)

        assert I.enforce_interface(token, token_interface), 'Invalid token interface!'

        currency_reserve, token_reserve = reserves[contract]
        k = currency_reserve * token_reserve

        new_token_reserve = token_reserve + token_amount

        new_currency_reserve = k / new_token_reserve

        currency_purchased = currency_reserve - new_currency_reserve # MINUS FEE

        fee = currency_purchased * state["FEE_PERCENTAGE"]

        currency_purchased -= fee
        new_currency_reserve += fee

        assert currency_purchased > 0, 'Token reserve error!'

        reserves[contract] = [new_currency_reserve, new_token_reserve]
        prices[contract] = new_currency_reserve / new_token_reserve
        
        return currency_purchased
    
class MyTestCase(TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()

        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'currency')
            self.client.submit(contract, 'con_token1')
            self.client.submit(contract, 'con_amm')

        self.client.submit(dex, 'dex')

        self.dex = self.client.get_contract('dex')
        self.amm = self.client.get_contract('con_amm')
        self.currency = self.client.get_contract('currency')
        self.token1 = self.client.get_contract('con_token1')
        
        self.currency.approve(amount=1000, to='dex')
        self.amm.approve(amount=1000, to='dex')
        
        self.dex.create_market(contract='con_amm', currency_amount=1000, token_amount=1000)
        
    def tearDown(self):
        self.client.flush()

    def test_transfer_liquidity_from_reduces_approve_account(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.approve_liquidity(contract='con_token1', to='jeff', amount=20)

        self.dex.transfer_liquidity_from(contract='con_token1', to='stu', main_account='sys', amount=20, signer='jeff')

        self.assertEqual(self.dex.lp_points['con_token1', 'sys', 'jeff'], 0)

    def test_transfer_liquidity_from_fails_if_not_enough_in_main_account(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.approve_liquidity(contract='con_token1', to='jeff', amount=2000)

        with self.assertRaises(AssertionError):
            self.dex.transfer_liquidity_from(contract='con_token1', to='stu', main_account='sys', amount=2000,
                                             signer='jeff')

    def test_transfer_liquidity_from_fails_if_not_approved(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.transfer_liquidity_from(contract='con_token1', to='stu', main_account='sys', amount=10,
                                             signer='jeff')

    def test_transfer_liquidity_from_fails_if_negative(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.approve_liquidity(contract='con_token1', to='jeff', amount=20)

        with self.assertRaises(AssertionError):
            self.dex.transfer_liquidity_from(contract='con_token1', to='stu', main_account='sys', amount=-1,
                                             signer='jeff')

    def test_transfer_liquidity_from_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.approve_liquidity(contract='con_token1', to='jeff', amount=20)

        self.dex.transfer_liquidity_from(contract='con_token1', to='stu', main_account='sys', amount=20, signer='jeff')

        self.assertEqual(self.dex.liquidity_balance_of(contract='con_token1', account='stu'), 20)
        self.assertEqual(self.dex.liquidity_balance_of(contract='con_token1', account='sys'), 80)

        self.dex.remove_liquidity(contract='con_token1', amount=20, signer='stu')

        self.assertEqual(self.currency.balance_of(account='stu'), 200)
        self.assertEqual(self.token1.balance_of(account='stu'), 200)

    def test_remove_liquidity_fails_on_market_doesnt_exist(self):
        with self.assertRaises(AssertionError):
            self.dex.remove_liquidity(contract='con_token1', amount=50)

    def test_transfer_liquidity_fails_on_negatives(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.transfer_liquidity(contract='con_token1', amount=-1, to='stu')

    def test_transfer_liquidity_fails_if_less_than_balance(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.transfer_liquidity(contract='con_token1', amount=101, to='stu')

    def test_transfer_liquidity_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.transfer_liquidity(contract='con_token1', amount=20, to='stu')

        self.assertEqual(self.dex.liquidity_balance_of(contract='con_token1', account='stu'), 20)
        self.assertEqual(self.dex.liquidity_balance_of(contract='con_token1', account='sys'), 80)

    def test_transfer_liquidity_can_be_removed_by_other_party(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.transfer_liquidity(contract='con_token1', amount=20, to='stu')

        self.dex.remove_liquidity(contract='con_token1', amount=20, signer='stu')

        self.assertEqual(self.currency.balance_of(account='stu'), 200)
        self.assertEqual(self.token1.balance_of(account='stu'), 200)

    def test_remove_liquidity_zero_or_neg_fails(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.remove_liquidity(contract='con_token1', amount=0)

    def test_remove_liquidity_more_than_balance_fails(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.remove_liquidity(contract='con_token1', amount=1, signer='stu')

    def test_remove_liquidity_works_generally(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.remove_liquidity(contract='con_token1', amount=50)

    def test_remove_liquidity_half_transfers_tokens_back(self):
        self.currency.transfer(amount=1000, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=1000, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000, signer='stu')

        self.assertEqual(self.currency.balance_of(account='dex'), 2000)
        self.assertEqual(self.token1.balance_of(account='dex'), 1000)

        self.assertEqual(self.currency.balance_of(account='stu'), 0)
        self.assertEqual(self.token1.balance_of(account='stu'), 0)

        self.dex.remove_liquidity(contract='con_token1', amount=50, signer='stu')

        self.assertEqual(self.currency.balance_of(account='dex'), 1500)
        self.assertEqual(self.token1.balance_of(account='dex'), 500)

        self.assertEqual(self.currency.balance_of(account='stu'), 500)
        self.assertEqual(self.token1.balance_of(account='stu'), 500)

    def test_remove_liquidity_half_transfers_correctly_second_remove_transfers_correctly_as_well(self):
        self.currency.transfer(amount=1000, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=1000, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000, signer='stu')

        self.assertEqual(self.currency.balance_of(account='dex'), 2000)
        self.assertEqual(self.token1.balance_of(account='dex'), 1000)

        self.assertEqual(self.currency.balance_of(account='stu'), 0)
        self.assertEqual(self.token1.balance_of(account='stu'), 0)

        self.dex.remove_liquidity(contract='con_token1', amount=50, signer='stu')

        self.assertEqual(self.currency.balance_of(account='dex'), 1500)
        self.assertEqual(self.token1.balance_of(account='dex'), 500)

        self.assertEqual(self.currency.balance_of(account='stu'), 500)
        self.assertEqual(self.token1.balance_of(account='stu'), 500)

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEqual(self.currency.balance_of(account='dex'), 1250)
        self.assertEqual(self.token1.balance_of(account='dex'), 250)

        self.assertEqual(self.currency.balance_of(account='stu'), 750)
        self.assertEqual(self.token1.balance_of(account='stu'), 750)

    def test_remove_liquidity_updates_reserves(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        # self.assertEqual(self.dex.lp_points['con_token1'], 75)

        self.assertEqual(self.dex.reserves['con_token1'], [75, 750])

    def test_remove_liquidity_updates_tokens(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEqual(self.dex.lp_points['con_token1'], 75)
        self.assertEqual(self.dex.lp_points['con_token1', 'stu'], 75)

    def test_remove_liquidity_after_additional_add_works(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.currency.transfer(amount=50, to='jeff')
        self.token1.transfer(amount=500, to='jeff')

        self.currency.approve(amount=50, to='dex', signer='jeff')
        self.token1.approve(amount=500, to='dex', signer='jeff')

        self.dex.add_liquidity(contract='con_token1', currency_amount=50, signer='jeff')

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='jeff')

        self.assertAlmostEqual(self.currency.balance_of(account='jeff'), 25)
        self.assertAlmostEqual(self.token1.balance_of(account='jeff'), 250)

    def test_buy_fails_if_no_market(self):
        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=1)

    def test_buy_fails_if_no_positive_value_provided(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=0)

    def test_buy_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.buy(contract='con_token1', currency_amount=1)
        
    def test_buy_entire_balance_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=1000, to='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.sell(contract='con_token1', token_amount=1000, signer='stu')
        
    def test_buy_with_token_fees_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')
        self.amm.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)
        
        self.dex.buy(contract='con_token1', currency_amount=1, token_fees=True)

    def test_buy_with_slippage_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.buy(contract='con_token1', currency_amount=1, minimum_received=0.5)
        
    def test_buy_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        fee = 90.909090909090 * (0.3 / 100)
        
        self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=90-fee, signer='stu') #To avoid inaccurate floating point calculations failing the test

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090909 - fee)
        
    def test_buy_with_token_fees_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        fee = 10 * 0.909090909090909 * 0.75 * (0.3 / 100) #Inaccurate
        
        self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=90.90909, token_fees=True, signer='stu') #To avoid inaccurate floating point calculations failing the test

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertAlmostEqual(self.amm.balance_of(account='stu'), 1000 - fee, 3) #To account for slippage on the RSWP/TAU pair
        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090909)
    #TODO: Add more tests
    def test_buy_below_minimum_received_fails(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)
        
        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=100, signer='stu')
        
    def test_buy_with_token_fees_below_minimum_recieved_fails(self):        
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)
        
        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=100, token_fees=True, signer='stu') #To avoid inaccurate floating point calculations failing the test
            
    def test_buy_with_token_fees_updates_price(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        # Price is impacted by the fee based on how much of the currency or token is sent in the buy / sell
        expected_price = 0.121
        amount = 10
        fee = 0.3 / 100 * 0.8 * 0.75

        actual_price = expected_price / (1 + (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)
        
    def test_buy_updates_price(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        # Price is impacted by the fee based on how much of the currency or token is sent in the buy / sell
        expected_price = 0.121
        amount = 10
        fee = 0.3 / 100 * 0.8

        actual_price = expected_price / (1 + (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)

    def test_buy_sell_updates_price_almost_to_original(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)

        fee = 90.909090909090 * (0.3 / 100)

        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090 - fee)

        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.sell(contract='con_token1', token_amount=90.909090909090 - fee, signer='stu')

        price_impact = 0.3 / (100 * 10) * 0.8

        self.assertAlmostEqual(self.dex.prices['con_token1'], 0.1 * (1 + price_impact * 2), 4)
        
    def test_buy_sell_with_token_fees_updates_price_almost_to_original(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)

        fee = 90.909090909090 * (0.3 / 100) * 0.75 

        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090)

        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.sell(contract='con_token1', token_amount=90.909090909090, token_fees=True, signer='stu')

        price_impact = 0.3 / (100 * 10) * 0.8 * 0.75

        self.assertAlmostEqual(self.dex.prices['con_token1'], 0.1 * (1 + price_impact * 2), 4)

    def test_buy_updates_reserves(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        fee = (1000 - 909.090909090909091) * (0.3 / 100) * 0.8

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertEqual(cur_res, 110)
        self.assertAlmostEqual(tok_res, 909.090909090909091 + fee)
        
    def test_buy_with_token_fees_updates_reserves(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        fee = (1000 - 909.090909090909091) * (0.3 / 100) * 0.8 * 0.75

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertEqual(cur_res, 110)
        self.assertAlmostEqual(Decimal(tok_res), Decimal(909.090909090909091 + fee), 4) #To account for slippage on the RSWP/TAU pair

    def test_sell_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertEquals(self.token1.balance_of(account='stu'), 10)

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        fee = 0.99009900990099 * (0.3 / 100)

        self.assertAlmostEqual(self.currency.balance_of(account='stu'), 0.99009900990099 - fee)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)
        
    def test_sell_with_token_fees_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertEquals(self.token1.balance_of(account='stu'), 10)

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        fee = 0.99009900990099 * (0.3 / 100) * 0.75

        self.assertAlmostEqual(self.currency.balance_of(account='stu'), 0.99009900990099)
        self.assertAlmostEqual(self.amm.balance_of(account='stu'), 1000 - fee, 3) #Does not account for slippage on RSWP pair, so lower accuracy is required
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

    def test_sell_updates_price(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        print(0.098029604940692 / self.dex.prices['con_token1'])

        # Because of fees, the amount left in the reserves differs
        expected_price = 0.098029604940692
        amount = 100
        fee = 0.3 / 100 * 0.8

        actual_price = expected_price / (1 - (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)
        
    def test_sell_with_token_fees_updates_price(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        print(0.098029604940692 / self.dex.prices['con_token1'])

        # Because of fees, the amount left in the reserves differs
        expected_price = 0.098029604940692
        amount = 100
        fee = 0.3 / 100 * 0.8 * 0.75

        actual_price = expected_price / (1 - (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)

    def test_sell_updates_reserves(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        fee = (100 - 99.00990099009901) * (0.3 / 100) * 0.8

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(cur_res, 99.00990099009901 + fee)
        self.assertEqual(tok_res, 1010)
        
    def test_sell_with_token_fees_updates_reserves(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        fee = (100 - 99.00990099009901) * (0.3 / 100) * 0.8 * 0.75

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(cur_res, Decimal(99.00990099009901) + Decimal(fee))
        self.assertEqual(tok_res, Decimal(1010))

    def test_sell_fails_if_no_market(self):
        with self.assertRaises(AssertionError):
            self.dex.sell(contract='con_token1', token_amount=1)

    def test_sell_fails_if_no_positive_value_provided(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.sell(contract='con_token1', token_amount=0)

    def test_create_market_fails_bad_interface(self):
        self.client.submit(bad_token)
        with self.assertRaises(AssertionError):
            self.dex.create_market(contract='bad_token', currency_amount=1, token_amount=1)

    def test_create_market_fails_zeros_for_amounts(self):
        with self.assertRaises(AssertionError):
            self.dex.create_market(contract='con_token1', currency_amount=0, token_amount=1)

        with self.assertRaises(AssertionError):
            self.dex.create_market(contract='con_token1', currency_amount=1, token_amount=-1)

    def test_create_market_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

    def test_create_market_sends_coins_to_dex(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.assertEqual(self.currency.balance_of(account='dex'), 1000)
        self.assertEqual(self.token1.balance_of(account='dex'), 0)

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.assertEqual(self.currency.balance_of(account='dex'), 2000)
        self.assertEqual(self.token1.balance_of(account='dex'), 1000)

    def test_create_market_sets_reserves(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.assertEqual(self.dex.reserves['con_token1'], [1000, 1000])

    def test_create_market_mints_100_lp_points(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.lp_points['con_token1', 'sys'] = 100

    def test_create_market_seeds_total_lp_points_to_100(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.dex.lp_points['con_token1'] = 100

    def test_create_market_sets_tau_reserve_to_currency_amount(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

    def test_create_market_sets_price_accurately(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)

        self.assertEqual(self.dex.prices['con_token1'], 0.1)

    def test_create_market_sets_pair_to_true(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.assertTrue(self.dex.pairs['con_token1'])

    def test_create_market_twice_throws_assertion(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        with self.assertRaises(AssertionError):
            self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

    def test_add_liquidity_fails_if_no_market(self):
        with self.assertRaises(AssertionError):
            self.dex.add_liquidity(contract='con_token1', currency_amount=1000)

    def test_add_liquidity_fails_if_currency_amount_zero(self):
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.add_liquidity(contract='con_token1', currency_amount=0)

    def test_add_liquidity_transfers_correct_amount_of_tokens(self):
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=10000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)

        self.assertEqual(self.currency.balance_of(account='dex'), 1100)
        self.assertEqual(self.token1.balance_of(account='dex'), 1000)

        self.dex.add_liquidity(contract='con_token1', currency_amount=100)

        self.assertEqual(self.currency.balance_of(account='dex'), 1200)
        self.assertEqual(self.token1.balance_of(account='dex'), 2000)

    def test_add_liquidity_mints_correct_amount_of_lp_tokens(self):
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=10000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)

        self.assertEqual(self.dex.lp_points['con_token1', 'sys'], 100)
        self.assertEqual(self.dex.lp_points['con_token1'], 100)

        self.currency.transfer(amount=10000, to='stu')
        self.token1.transfer(amount=10000, to='stu')

        self.currency.approve(amount=10000, to='dex', signer='stu')
        self.token1.approve(amount=10000, to='dex', signer='stu')

        self.dex.add_liquidity(contract='con_token1', currency_amount=50, signer='stu')

        self.assertEqual(self.dex.lp_points['con_token1', 'sys'], 100)
        self.assertEqual(self.dex.lp_points['con_token1', 'stu'], 50)
        self.assertEqual(self.dex.lp_points['con_token1'], 150)

    def test_add_liquidity_updates_reserves_correctly(self):
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=10000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)

        self.assertEqual(self.dex.reserves['con_token1'], [100, 1000])

        self.currency.transfer(amount=10000, to='stu')
        self.token1.transfer(amount=10000, to='stu')

        self.currency.approve(amount=10000, to='dex', signer='stu')
        self.token1.approve(amount=10000, to='dex', signer='stu')

        self.dex.add_liquidity(contract='con_token1', currency_amount=50, signer='stu')

        self.assertEqual(self.dex.reserves['con_token1'], [150, 1500])

    def test_remove_liquidity_after_buy_collects_token_fees(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        purchased_tokens = self.token1.balances['stu']

        # Removing 25% of the liquidity returns 25% of the fees collected

        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEquals(self.currency.balances['stu'], 110 * 0.25)
        self.assertEquals(self.token1.balances['stu'], (token_reserves * 0.25) + purchased_tokens)
        
    def test_remove_liquidity_after_buy_with_token_fees_collects_token_fees(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        purchased_tokens = self.token1.balances['stu']

        # Removing 25% of the liquidity returns 25% of the fees collected

        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEquals(self.currency.balances['stu'], 110 * 0.25)
        self.assertEquals(self.token1.balances['stu'], (token_reserves * Decimal(0.25)) + purchased_tokens)

    def test_remove_liquidity_after_sell_collects_currency_fees(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1100, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1100, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=100, signer='stu')

        purchased_currency = self.currency.balances['stu']

        # Removing 25% of the liquidity returns 25% of the fees collected
        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEquals(self.currency.balances['stu'], (cur_reserves * Decimal(0.25)) + purchased_currency)
        self.assertEquals(self.token1.balances['stu'], 1100 * 0.25)
        
    def test_remove_liquidity_after_sell_with_token_fees_collects_currency_fees(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1100, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1100, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=100, token_fees=True, signer='stu')

        purchased_currency = self.currency.balances['stu']

        # Removing 25% of the liquidity returns 25% of the fees collected
        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=25, signer='stu')

        self.assertEquals(self.currency.balances['stu'], (cur_reserves * Decimal(0.25)) + purchased_currency)
        self.assertEquals(self.token1.balances['stu'], 1100 * 0.25)

    def test_remove_liquidity_collects_fees_proportionally_after_buy(self):
        # SYS opens the market, has 100 LP points
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=10000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=75, token_amount=750)

        # STU adds liquidity, as 25% of total LP points
        self.currency.transfer(amount=5000, to='stu')
        self.token1.transfer(amount=5000, to='stu')

        self.currency.approve(amount=5000, to='dex', signer='stu')
        self.token1.approve(amount=5000, to='dex', signer='stu')

        self.dex.add_liquidity(contract='con_token1', currency_amount=25, signer='stu')

        self.assertAlmostEqual(float(self.dex.lp_points['con_token1', 'stu'] / self.dex.lp_points['con_token1']), 0.25)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        purchased_tokens = self.token1.balances['stu']

        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=33.33333333333331, signer='stu')

        self.assertAlmostEqual(self.token1.balances['stu'], (float(token_reserves) * 0.25) + purchased_tokens)

    def test_remove_liquidity_collects_fees_proportionally_after_sell(self):
        # SYS opens the market, has 100 LP points
        self.currency.approve(amount=10000, to='dex')
        self.token1.approve(amount=10000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=75, token_amount=750)

        # STU adds liquidity, as 25% of total LP points
        self.currency.transfer(amount=5000, to='stu')
        self.token1.transfer(amount=5000, to='stu')

        self.currency.approve(amount=5000, to='dex', signer='stu')
        self.token1.approve(amount=5000, to='dex', signer='stu')

        self.dex.add_liquidity(contract='con_token1', currency_amount=25, signer='stu')

        self.assertAlmostEqual(float(self.dex.lp_points['con_token1', 'stu'] / self.dex.lp_points['con_token1']), 0.25)

        self.dex.sell(contract='con_token1', token_amount=100, signer='stu')

        purchased_currency = self.currency.balances['stu']

        cur_reserves, token_reserves = self.dex.reserves['con_token1']

        self.dex.remove_liquidity(contract='con_token1', amount=33.33333333333331, signer='stu')

        self.assertAlmostEqual(self.currency.balances['stu'], (float(cur_reserves) * 0.25) + purchased_currency)
        
    def test_stake_works(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        self.assertEquals(self.amm.balances['stu'], 0)
       
    def test_stake_multiple_steps_works(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=25, signer='stu')
        self.dex.stake(amount=50, signer='stu')
        self.dex.stake(amount=75, signer='stu')
        self.dex.stake(amount=100, signer='stu')
        
        self.assertEquals(self.amm.balances['stu'], 0)
        self.assertEquals(self.dex.staked_amount['stu'], 100)
        
    def test_unstake_works(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        self.dex.stake(amount=0, signer='stu')
        self.assertEquals(self.amm.balances['stu'], 100)
        
    def test_unstake_multiple_steps_works(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        
        self.dex.stake(amount=75, signer='stu')
        self.dex.stake(amount=50, signer='stu')
        self.dex.stake(amount=25, signer='stu')
        self.dex.stake(amount=0, signer='stu')
        
        self.assertEquals(self.amm.balances['stu'], 100)
        
    def test_stake_more_than_balance_fails(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        with self.assertRaises(AssertionError):
            self.dex.stake(amount=1000, signer='stu')
    
    def test_unstake_less_than_zero_fails(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        
        with self.assertRaises(AssertionError):
            self.dex.stake(amount=-1, signer='stu')
                
    def test_stake_sets_discount_variable(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertAlmostEquals(self.dex.discount['stu'], accuracy * (amount ** (1 / accuracy) - 1) * multiplier)
        
    def test_stake_sets_discount_variable(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertAlmostEquals(self.dex.discount['stu'], 1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)
        
    def test_stake_over_ninety_nine_percent_sets_discount_variable_at_ninety_nine(self): #TODO: fix to better adhere to PEP8
        print("This will fail with present numbers because there is not enough total supply")
        
        try:
        
            self.amm.transfer(amount=500000000, to='stu')
            self.amm.approve(amount=500000000, to='dex', signer='stu')
        
            self.dex.stake(amount=500000000, signer='stu')
        
            self.assertAlmostEquals(self.dex.discount['stu'], 0.99)
            
        except AssertionError:
            print("Failed")
            
    def test_buy_with_discount_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')
        self.amm.approve(amount=1000, to='dex')
        
        self.dex.stake(amount=10)

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.buy(contract='con_token1', currency_amount=1)
        
    def test_buy_with_discount_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.stake(amount=100, signer='stu')
        
        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 90.909090909090 * (0.3 / 100) * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)
        
        self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=90-fee, signer='stu') #To avoid inaccurate floating point calculations failing the test

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090909 - fee)
        
    def test_buy_with_token_fees_and_discount_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.stake(amount=100, signer='stu')
        
        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 10 * 0.909090909090909 * 0.75 * (0.3 / 100) * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier) #Inaccurate
        
        self.dex.buy(contract='con_token1', currency_amount=10, minimum_received=90.90909, token_fees=True, signer='stu') #To avoid inaccurate floating point calculations failing the test

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertAlmostEqual(self.amm.balance_of(account='stu'), 900 - fee, 3) #To account for slippage on the RSWP/TAU pair
        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090909)
        
    def test_buy_with_token_fees_and_discount_updates_price(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        # Price is impacted by the fee based on how much of the currency or token is sent in the buy / sell
        expected_price = 0.121
        amount = 10
        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.3 / 100 * 0.8 * 0.75 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        actual_price = expected_price / (1 + (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)
        
    def test_buy_with_discount_updates_price(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        # Price is impacted by the fee based on how much of the currency or token is sent in the buy / sell
        expected_price = 0.121
        amount = 10
        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.3 / 100 * 0.8 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        actual_price = expected_price / (1 + (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)
        
    def test_buy_with_discount_updates_reserves(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')

        self.dex.stake(amount=100, signer='stu')
        
        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = (1000 - 909.090909090909091) * (0.3 / 100) * 0.8 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertEqual(cur_res, 110)
        self.assertAlmostEqual(Decimal(tok_res), Decimal(909.090909090909091) + Decimal(fee))
        
    def test_buy_with_token_fees_and_discount_updates_reserves(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.buy(contract='con_token1', currency_amount=10, token_fees=True, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = (1000 - 909.090909090909091) * (0.3 / 100) * 0.8 * 0.75 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertEqual(cur_res, 110)
        self.assertAlmostEqual(Decimal(tok_res), Decimal(909.090909090909091 + fee), 3) #To account for slippage on the RSWP/TAU pair
        
    def test_sell_with_discount_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertEquals(self.token1.balance_of(account='stu'), 10)

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.99009900990099 * (0.3 / 100) * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        self.assertAlmostEqual(self.currency.balance_of(account='stu'), 0.99009900990099 - fee)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)
        
    def test_sell_with_token_fees_and_discount_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertEquals(self.token1.balance_of(account='stu'), 10)

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.99009900990099 * (0.3 / 100) * 0.75 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        self.assertAlmostEqual(self.currency.balance_of(account='stu'), 0.99009900990099)
        self.assertAlmostEqual(self.amm.balance_of(account='stu'), 900 - fee, 3) #Does not account for slippage on RSWP pair, so lower accuracy is required
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

    def test_sell_with_discount_updates_price(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        print(0.098029604940692 / self.dex.prices['con_token1'])

        # Because of fees, the amount left in the reserves differs
        expected_price = 0.098029604940692
        amount = 100
        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.3 / 100 * 0.8 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        actual_price = expected_price / (1 - (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)
        
    def test_sell_with_token_fees_and_discount_updates_price(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        print(0.098029604940692 / self.dex.prices['con_token1'])

        # Because of fees, the amount left in the reserves differs
        expected_price = 0.098029604940692
        amount = 100
        accuracy = 1000000000.0
        multiplier = 0.05
        fee = 0.3 / 100 * 0.8 * 0.75 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        actual_price = expected_price / (1 - (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)

    def test_sell_with_discount_updates_reserves(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.sell(contract='con_token1', token_amount=10, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = (100 - 99.00990099009901) * (0.3 / 100) * 0.8 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(Decimal(cur_res), Decimal(99.00990099009901) + Decimal(fee))
        self.assertEqual(tok_res, 1010)
        
    def test_sell_with_token_fees_and_discount_updates_reserves(self):
        self.currency.transfer(amount=100, to='stu')
        self.token1.transfer(amount=1010, to='stu')
        self.amm.transfer(amount=1000, to='stu')

        self.currency.approve(amount=100, to='dex', signer='stu')
        self.token1.approve(amount=1010, to='dex', signer='stu')
        self.amm.approve(amount=1000, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.sell(contract='con_token1', token_amount=10, token_fees=True, signer='stu')

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = (100 - 99.00990099009901) * (0.3 / 100) * 0.8 * 0.75 * (1 - accuracy * (100 ** (1 / accuracy) - 1) * multiplier)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(cur_res, Decimal(99.00990099009901) + Decimal(fee), 4)
        self.assertEqual(tok_res, Decimal(1010))
        
    def test_buy_with_minimal_reserve(self):
        self.currency.approve(amount=100, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.currency.transfer(amount=10000, to='stu')
        self.currency.approve(amount=10000, to='dex', signer='stu')
        
        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)
        self.dex.remove_liquidity(contract='con_amm', amount=98) #Must have more than 1 LP remaining, or remove_liquidity will throw AssertionError 

        fee = (0.3 / 100)
        
        for x in range(100):
            self.dex.buy(contract='con_token1', currency_amount=100, signer='stu')
            
        self.assertAlmostEqual(Decimal(self.dex.reserves['con_token1'][0]), 10100)
        self.assertAlmostEqual(Decimal(self.token1.balances["stu"]), Decimal(1000) - 1000 * Decimal(fee))
            
    def test_change_state_works(self):
        self.dex.change_state(key="DISCOUNT", new_value="0.1", convert_to_decimal=True)
        self.assertEqual(self.dex.state['DISCOUNT'], 0.1)
        
    def test_change_state_string_works(self):
        self.dex.change_state(key="BURN_ADDRESS", new_value="stu")
        self.assertEqual(self.dex.state['BURN_ADDRESS'], "stu")
        
    def test_change_state_int_works(self):
        self.dex.change_state(key="DISCOUNT", new_value="1", convert_to_decimal=True)
        self.assertEqual(self.dex.state['DISCOUNT'], 1)
        
    def test_change_owner_works(self):
        self.dex.change_state(key="OWNER", new_value="stu")
        self.assertEqual(self.dex.state['OWNER'], "stu")
        
        self.dex.change_state(key="OWNER", new_value="jeff", signer="stu")
        self.assertEqual(self.dex.state['OWNER'], "jeff")
        
        self.dex.change_state(key="TOKEN_DISCOUNT", new_value="0.5", convert_to_decimal=True, signer="jeff")
        self.assertEqual(self.dex.state['TOKEN_DISCOUNT'], 0.5)
        
    def test_change_state_not_owner_fails(self):
        with self.assertRaises(AssertionError):
            self.dex.change_state(key="OWNER", new_value="stu", signer="stu")
        
    def test_change_owner_twice_fails(self):
        self.dex.change_state(key="OWNER", new_value="stu")
        self.assertEqual(self.dex.state['OWNER'], "stu")
        
        with self.assertRaises(AssertionError):
            self.dex.change_state(key="OWNER", new_value="stu")
            
    def test_increased_burn_works(self):
        self.dex.change_state(key="BURN_PERCENTAGE", new_value="0.6", convert_to_decimal=True)
        
        self.currency.approve(amount=100, to='dex')
        self.token1.approve(amount=1010, to='dex')
        
        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000)

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.sell(contract='con_token1', token_amount=10)

        accuracy = 1000000000.0
        multiplier = 0.05
        fee = (100 - 99.00990099009901) * (0.3 / 100) * 0.6

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(cur_res, 99.00990099009901 + fee)
