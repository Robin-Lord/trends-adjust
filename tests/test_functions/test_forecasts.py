import unittest
import pandas as pd
import process_forecast as pf


class testPandas(unittest.TestCase):
    def setUp(self) -> None:
        self.file = pd.read_csv("tests/test_files/example_forecast.csv")

    def test_reverse_engineer_forecast(self):
        forecast_df = self.file
        multiplier = 1



        returned_df = pf.reverse_engineer_forecast_for_trend(
                forecast_df = forecast_df,
                multiplier = multiplier,
                )

        # When the multiplier is 1 there should be no change
        self.assertAlmostEqual(returned_df["yhat"].sum(), returned_df["yhat_adjusted"].sum())


        # When the multiplier is 0 then "yhat_adjusted" should match "yhat_zero_trend"
        multiplier = 0

        returned_df = pf.reverse_engineer_forecast_for_trend(
                forecast_df = forecast_df,
                multiplier = multiplier,
                )

        # When the multiplier is 1 there should be no change
        self.assertAlmostEqual(returned_df["yhat_zero_trend"].sum(), returned_df["yhat_adjusted"].sum())

        # Whern the multiplier is 0.5 the adjusted value should be half way
        # between the standard value and the zero trend value
        # The same goes for any proportional value of our multiplier
        for multiplier in range(0, 11, 1):
            multiplier = multiplier/10
            returned_df = pf.reverse_engineer_forecast_for_trend(
                    forecast_df = forecast_df,
                    multiplier = multiplier,
                    )
            
            base_forecast_total = returned_df["yhat"].sum()
            zero_trend_forecast_total = returned_df["yhat_zero_trend"].sum()
            adjusted_forecast_total = returned_df["yhat_adjusted"].sum()

            difference = base_forecast_total-zero_trend_forecast_total
            part_way = zero_trend_forecast_total+(difference*multiplier)
            
            self.assertAlmostEqual(adjusted_forecast_total, part_way)

            print(f"Multiplier '{multiplier}' sucess. Total = {adjusted_forecast_total}")

            import pdb
            pdb.set_trace()
            