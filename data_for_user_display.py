import data_for_user_functions
import db_logging


def main():

    while True:

        print("")

        menu_input = input(data_for_user_functions.print_menu())

        if menu_input == "exit":
            print("Goodbye")
            break

        try:
            menu_choice = int(menu_input)
        except ValueError:
            print("Please enter a number between 1 and 7, or type 'exit'")
            continue

        match menu_choice:
            # display account balance
            case 1:
                data_for_user_functions.display_current_account_balance()
            # display account balance over time
            case 2:
                data_for_user_functions.display_account_balance_over_time()
            # display a particular trade
            case 3:
                trade_id = input("Enter your trade_id: ")
                trade = db_logging.get_trade(trade_id)

                if trade is None:
                    print("Trade ID does not exist")
                else:
                    data_for_user_functions.display_trade(trade_id)
            # display a particular position
            case 4:
                symbol = input("Enter your symbol: ").upper()
                position = db_logging.get_position(symbol)

                if position is None:
                    print("No open position found for this symbol")
                else:
                    data_for_user_functions.display_position(symbol)
            # display all trades made today
            case 5:
                data_for_user_functions.display_all_trades_today()
            # display all positions
            case 6:
                data_for_user_functions.display_all_positions()
            # display all trades
            case 7:
                data_for_user_functions.display_all_trades()
            case _:
                print("Menu option must be between 1 and 7")


if __name__ == "__main__":
    main()