import unittest
import pandas_helpers as pdh
import pandas as pd
import os

class testPandas(unittest.TestCase):
    def setUp(self) -> None:

        self.date_col = "ds"

        self.default_args = {
            "date_col": self.date_col,
            "target_col": "y",
            "regressor_cols": []
        }

        # Standard downloaded csv which has every row filled and is in date order
        self.file_full = pd.read_csv(
            "tests/test_files/example_wp_log_peyton_manning.csv"
        )

        # Date ordered csv with some rows missing
        self.file_with_missing = pd.read_csv(
            "tests/test_files/example_wp_log_peyton_manning_data_gaps.csv"
            )
        
        # Full csv but not in date order
        self.file_disordered = pd.read_csv(
            "tests/test_files/example_wp_log_peyton_manning_reordered.csv"
        )

        self.secondary_file = pd.read_csv(
            "tests/test_files/example_data_2.csv"
        )


        return super().setUp()

    def test_mistmatch_error(self) -> None:
        
        arguments = {
            "df": self.file_with_missing,
            "date_col": "ds",
            "target_col": "y",
            "regressor_cols": []
        }

        self.assertRaises(ValueError, pdh.check_and_convert_data, **arguments)
        
    def test_rejecting_reorder(self) -> None:

        converted_disordered_file: pd.DataFrame = pdh.date_col_conversion(
            df = self.file_disordered, 
            date_col = self.date_col)

        arguments = {
            "df": converted_disordered_file,
            "date_col": "ds"
         } 
        
        # Flag to automatically decline reordering, should raise error
        os.environ["AUTO_YES_NO"] = "no"
        self.assertRaises(ValueError, pdh.check_ordering, **arguments)

        # Flag to auto agree to reordering, should return df identical
        # to the standard csv
        os.environ["AUTO_YES_NO"] = "yes"
        reordered_df, should_continue = pdh.check_ordering(
            **arguments # type: ignore
            )
        
        self.assertTrue(should_continue)
        print(f"should_continue is True: {should_continue == True}")

        full_file_converted = pdh.date_col_conversion(
            df = self.file_full, 
            date_col = self.date_col)


        print(f"""
Comparing dataframes after reordering:
              
Columns match: {reordered_df.dtypes.equals(full_file_converted.dtypes)}
Row count match: {len(reordered_df[self.date_col]) == len(full_file_converted[self.date_col])}
Reordered df is monotonic: {reordered_df[self.date_col].is_monotonic_increasing}              
Original df is monotonic: {full_file_converted[self.date_col].is_monotonic_increasing}              
Dataframes match: {reordered_df.equals(full_file_converted)}              
              """)


        self.assertTrue(reordered_df.equals(full_file_converted))



    def test_secondary_data(self):
        date_col = "ds"


        converted_file = pd.DataFrame = pdh.date_col_conversion(
            df = self.secondary_file, 
            date_col = date_col)

        arguments = {
            "df": converted_file,
            "date_col": "ds"
         }         


        # Flag to auto agree to reordering, should return df identical
        # to the standard csv
        os.environ["AUTO_YES_NO"] = "yes"
        reordered_df, should_continue = pdh.check_ordering(
            **arguments # type: ignore
            )
        
        self.assertTrue(should_continue)
        print(f"should_continue is True: {should_continue == True}")

        full_file_converted = pdh.date_col_conversion(
            df = self.file_full, 
            date_col = self.date_col)

        import pdb
        pdb.set_trace()