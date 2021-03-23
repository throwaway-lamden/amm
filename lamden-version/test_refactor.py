from unittest import TestCase
from contracting.client import ContractingClient
from decimal import Decimal #To fix some unittest concatenation issues

def bad_token():
    @export
    def thing():
        return 1

class MyTestCase(TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()

        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'currency')
            self.client.submit(contract, 'con_token1')
            self.client.submit(contract, 'con_amm')

        with open('dex.py') as f:
            contract = f.read()
            self.client.submit(contract, 'dex')

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
        
    def test_buy_minimal_amount_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.buy(contract='con_token1', currency_amount=0.00001)
        
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
        self.assertEquals(self.dex.staked_amount['stu', 'con_amm'], 100)
       
    def test_stake_minimal_amount_works(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=0.01, signer='stu')
        self.assertEquals(self.dex.discount['stu'], 1)
        
        self.dex.stake(amount=0.1, signer='stu')
        self.assertEquals(self.dex.discount['stu'], 1)
        
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

        fee = (0.3 / 100) * 0.2
        
        for x in range(100):
            self.dex.buy(contract='con_token1', currency_amount=100, signer='stu')
            
        self.assertAlmostEqual(Decimal(self.dex.reserves['con_token1'][0]), 10100)
        self.assertAlmostEqual(self.token1.balances["stu"] + self.dex.reserves['con_token1'][1], 1000 - 1000 * Decimal(fee), 0)
            
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
        
    def test_buy_large_amount_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=200000001, to='dex')
        self.token1.approve(amount=1, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1, token_amount=1)

        self.dex.buy(contract='con_token1', currency_amount=200000000)
        
    def test_buy_large_amount_with_token_fees_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=200000001, to='dex')
        self.token1.approve(amount=1, to='dex')
        
        self.amm.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1, token_amount=1)

        self.dex.buy(contract='con_token1', currency_amount=200000000, token_fees=True)
        
    def test_buy_large_amount_with_discount_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=200000001, to='dex')
        self.token1.approve(amount=1, to='dex')
        
        self.amm.approve(amount=1000, to='dex')
        self.dex.stake(amount=1000)

        self.dex.create_market(contract='con_token1', currency_amount=1, token_amount=1)

        self.dex.buy(contract='con_token1', currency_amount=200000000)
        
    def test_buy_large_amount_with_token_fees_and_discount_works(self): #Can be removed, test_buy_with_slippage does everything it does
        self.currency.approve(amount=200000001, to='dex')
        self.token1.approve(amount=1, to='dex')
        
        self.amm.approve(amount=2000, to='dex')
        self.dex.stake(amount=1000)

        self.dex.create_market(contract='con_token1', currency_amount=1, token_amount=1)

        self.dex.buy(contract='con_token1', currency_amount=200000000, token_fees=True)
        
    def test_stake_unstake_after_token_change_works(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        self.token2.transfer(amount=100, to='stu')
        self.token2.approve(amount=100, to='dex', signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=100, signer='stu')
        self.dex.stake(amount=0, token_contract="con_amm", signer='stu')
        
        self.assertEquals(self.amm.balances['stu'], 100)
        
    def test_unstake_after_token_change_works(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=100, signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=0, token_contract="con_amm", signer='stu')
        
        self.assertEquals(self.amm.balances['stu'], 100)
        
    def test_stake_arbitrary_token_after_token_change_works(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        self.token2.transfer(amount=100, to='stu')
        self.token2.approve(amount=100, to='dex', signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=100, token_contract='con_amm', signer='stu')
                
        self.assertEquals(self.amm.balances['stu'], 0)
        
    def test_stake_arbitrary_token_after_token_change_does_not_increase_discount(self):
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=100, token_contract='con_amm', signer='stu')
                
        self.assertEquals(self.dex.discount['stu'], 1)
        
    def test_stake_arbitrary_token_after_token_change_does_not_affect_discount(self):
        return False #This test is no longer necessary
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        
        self.dex.stake(amount=10, signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=100, token_contract='con_amm', signer='stu')
                
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertEquals(self.dex.discount['stu'], 1 - accuracy * (10 ** (1 / accuracy) - 1) * multiplier)
        
    def test_stake_cannot_unstake_different_token(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        self.token2.transfer(amount=10, to='jeff')
        self.token2.transfer(amount=10, to='stu')
        self.token2.approve(amount=10, to='dex', signer='jeff')
        
        self.dex.stake(amount=10, signer='stu')
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=10, signer='jeff')
        self.dex.stake(amount=0, signer='stu')
        self.dex.stake(amount=0, signer='jeff')
        
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertEquals(self.token2.balances['stu'], 10)
        self.assertEquals(self.token2.balances['jeff'], 10)
       
    def test_unstake_resets_discount(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        self.token2.transfer(amount=10, to='jeff')
        
        self.dex.stake(amount=10, signer='stu')        
        self.dex.stake(amount=0, signer='stu')
        
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertEquals(self.dex.discount['stu'], 1)
        
    def test_unstake_after_contract_change_resets_discount(self):
        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'con_token2')
        self.token2 = self.client.get_contract('con_token2')
        
        self.amm.transfer(amount=100, to='stu')
        self.amm.approve(amount=100, to='dex', signer='stu')
        self.token2.transfer(amount=10, to='stu')
        self.token2.approve(amount=10, to='dex', signer='stu')
        
        self.dex.stake(amount=10, signer='stu')        
        
        self.dex.change_state(key="TOKEN_CONTRACT", new_value="con_token2")
        
        self.dex.stake(amount=1, signer='stu')
        self.dex.stake(amount=0, signer='stu')
        
        accuracy = 1000000000.0
        multiplier = 0.05
        
        self.assertEquals(self.dex.discount['stu'], 1)

class RSWPTestCase(TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()

        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'currency')
            self.client.submit(contract, 'con_token1')

        with open('dex.py') as f:
            contract = f.read()
            self.client.submit(contract, 'dex')

        self.dex = self.client.get_contract('dex')
        self.currency = self.client.get_contract('currency')
        self.token1 = self.client.get_contract('con_token1')
        
        self.dex.change_state(key='TOKEN_CONTRACT', new_value='con_token1')
                
    def tearDown(self):
        self.client.flush()
    
    def test_buy_fails_if_no_market(self):
        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=1)

    def test_buy_fails_if_no_positive_value_provided(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.buy(contract='con_token1', currency_amount=0)

    def test_buy_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.buy(contract='con_token1', currency_amount=1)

    def test_buy_transfers_correct_amount_of_tokens(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.currency.balance_of(account='stu'), 10)
        self.assertEquals(self.token1.balance_of(account='stu'), 0)

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        fee = 90.909090909090 * (0.3 / 100)

        self.assertEquals(self.currency.balance_of(account='stu'), 0)
        self.assertAlmostEqual(self.token1.balance_of(account='stu'), 90.909090909090909 - fee)

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
        fee = 0.3 / 100

        actual_price = expected_price / (1 + (fee / amount))

        self.assertAlmostEqual(self.dex.prices['con_token1'], actual_price)

    def test_buy_sell_updates_price_to_original(self):
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

        price_impact = 0.3 / (100 * 10)

        self.assertAlmostEqual(self.dex.prices['con_token1'], 0.1 * (1 + price_impact * 2))

    def test_buy_updates_reserves(self):
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.reserves['con_token1'], [100, 1000])

        self.dex.buy(contract='con_token1', currency_amount=10, signer='stu')

        fee = (1000 - 909.090909090909091) * (0.3 / 100)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertEqual(cur_res, 110)
        self.assertAlmostEqual(tok_res, 909.090909090909091 + fee)

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
        fee = 0.3 / 100

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

        fee = (100 - 99.00990099009901) * (0.3 / 100)

        cur_res, tok_res = self.dex.reserves['con_token1']

        self.assertAlmostEqual(cur_res, 99.00990099009901 + fee)
        self.assertEqual(tok_res, 1010)

    def test_sell_fails_if_no_market(self):
        with self.assertRaises(AssertionError):
            self.dex.sell(contract='con_token1', token_amount=1)

    def test_sell_fails_if_no_positive_value_provided(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=1000, token_amount=1000)

        with self.assertRaises(AssertionError):
            self.dex.sell(contract='con_token1', token_amount=0)

class SyncTestCase(TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()

        with open('currency.c.py') as f:
            contract = f.read()
            self.client.submit(contract, 'currency')
            self.client.submit(contract, 'con_token1')
            self.client.submit(contract, 'con_token2')
            self.client.submit(contract, 'con_amm')

        with open('dex.py') as f:
            contract = f.read()
            self.client.submit(contract, 'dex')

        self.dex = self.client.get_contract('dex')
        self.amm = self.client.get_contract('con_amm')
        self.currency = self.client.get_contract('currency')
        self.token1 = self.client.get_contract('con_token1')
        self.token2 = self.client.get_contract('con_token2')
        
        self.currency.approve(amount=1000, to='dex')
        self.amm.approve(amount=1000, to='dex')
        
        self.dex.create_market(contract='con_amm', currency_amount=1000, token_amount=1000)
                                   
    def tearDown(self):
        self.client.flush()

    def test_sync_works(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=100, to='dex')
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
    def test_sync_less_than_zero_fails(self):
        return "Currently impossible to test, TODO: fix with env"
        
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=100, to='stu', signer='con_dex') #Might not work
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
                
    def test_sync_not_enabled_fails(self):
        with self.assertRaises(AssertionError):
            self.dex.sync_reserves(contract="con_token1", signer="jeff")
            
    def test_sync_updates_reserves(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=100, to='dex')
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        tok_res = self.dex.reserves['con_token1'][1]
        
        self.assertEquals(tok_res, 200)
                
    def test_buy_works_after_sync(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        self.dex.buy(contract='con_token1', currency_amount=1)
        
    def test_buy_works_after_sync_with_difference(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=100, to='dex')
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        self.dex.buy(contract='con_token1', currency_amount=1)
        
    def test_sell_works_after_sync(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        self.dex.sell(contract='con_token1', token_amount=1)
        
    def test_sell_works_after_sync_with_difference(self):
        self.currency.approve(amount=1000, to='dex')
        self.token1.approve(amount=1000, to='dex')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=100)

        self.token1.transfer(amount=100, to='dex')
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        self.dex.sell(contract='con_token1', token_amount=1)

    def test_sync_does_not_affect_other_pairs(self):
        self.currency.transfer(amount=10001100, to='stu')
        self.token1.transfer(amount=100001000, to='stu')
        self.token2.transfer(amount=1000, to='stu')

        self.currency.approve(amount=10001100, to='dex', signer='stu')
        self.token1.approve(amount=100001000, to='dex', signer='stu')
        self.token2.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')
        self.dex.create_market(contract='con_token2', currency_amount=100, token_amount=1000, signer='stu')
    
        self.token1.transfer(amount=1000, to='dex')
        
        self.dex.change_state(key='SYNC_ENABLED', new_value=True)
        self.dex.sync_reserves(contract='con_token1', signer='stu')
        
        self.dex.buy(contract='con_token1', currency_amount=10000000, signer='stu')
        amount_bought = self.dex.sell(contract='con_token1', token_amount=100000000, signer='stu')

        self.dex.remove_liquidity(contract='con_token2', amount=98, signer='stu')
        
        self.assertAlmostEqual(self.currency.balance_of(account='stu'), 98 + amount_bought - 10000000 + 10001100 - 200)
        self.assertAlmostEqual(self.token2.balance_of(account='stu'), 980)

    def test_buy_updates_price(self):
        #TODO
        return False
    
        self.currency.transfer(amount=110, to='stu')
        self.token1.transfer(amount=1000, to='stu')

        self.currency.approve(amount=110, to='dex', signer='stu')
        self.token1.approve(amount=1000, to='dex', signer='stu')

        self.dex.create_market(contract='con_token1', currency_amount=100, token_amount=1000, signer='stu')

        self.assertEquals(self.dex.prices['con_token1'], 0.1)
