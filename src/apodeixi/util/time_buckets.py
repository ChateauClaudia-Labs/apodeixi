import datetime                                 as _datetime
import calendar                                 as _calendar

class FY_Quarter():
    '''
    Represents a quarter in the fiscal year. The fiscal year runs from the 1st of the month initialized in the constructure. Years are only supported
    from 2012 onwards.
    
    @param month_fiscal_year_starts: an integer, representing the month of the year when the fiscal year starts. Defaults to January
    @param year: an integer, representing a fiscal year. For example, 2022 represents the fiscal year from June 1st 2021 
                     to May 31st 2022.
    @param quarter: an integer between 1 and 4, representing a quarter. For example, if year=2022 then quarter=3 represents 
                    the 3 months from December 1st 2021 to February 28 2022.
    '''
    def __init__(self, fiscal_year, quarter, month_fiscal_year_starts=1):
        if fiscal_year < 2012:
            raise ValueError("Fiscal Year " + str(fiscal_year) + " is not supported as a valid year. Only years after 2012 are supported")
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter " + str(quarter) + " is not a valid quarter. Must be of of: 1, 2, 3, or 4")
        self.month_fiscal_year_starts   = month_fiscal_year_starts
        self.fiscal_year                = fiscal_year
        self.quarter                    = quarter
        
    def getQuarter(date, month_fiscal_year_starts):
        '''
        Returns a new FY_Quarter object that contains the given `date` parameter
        '''
        calendar_year = date.year
        # Search neighboring quarters for a match
        for fy in [calendar_year, calendar_year + 1]:
            for quarter in [1, 2, 3, 4]:
                candidate = FY_Quarter( fiscal_year                 = fy, 
                                        quarter                     = quarter, 
                                        month_fiscal_year_starts    = month_fiscal_year_starts)
                if candidate.contains(date):
                    return candidate
                
        # If we get this far we have a serious bug, since we should have found a quarter that contained the date
        assert(False)
        
    def contains(self, date):
        '''
        Returns True or False, depending on whether the given date falls within this quarter
        '''
        if date != None and self.first_day() <= date and date <= self.last_day():
            return True
        else:
            return False
           
    def last_day(self):
        '''
        Returns a datetime.date object, corresponding to the last day of the quarter
        '''
        month, year_delta  = self._ends_on_month()
        calendar_year      = self.fiscal_year + year_delta
        last_day_of_month  = _calendar.monthrange(calendar_year, month)[1]
        d = _datetime.date(calendar_year, month, last_day_of_month)
        return d
    
    def first_day(self):
        '''
        Returns a datetime.date object, corresponding to the first calendar day of this quarter.
        '''
        month, year_delta   = self._starts_on_month()
        calendar_year       = self.fiscal_year + year_delta
        first_day_of_month  = 1
        d = _datetime.date(calendar_year, month, first_day_of_month)
        return d
    
    def displayFY(self):
        return 'FY' + str(self.fiscal_year%100)
    
    def displayQuarter(self):
        return 'Q' + str(self.quarter)
    
    def _starts_on_month(self):
        '''
        Helper method to compute the calendar month when the quarter starts. 
        Returns two integers. The first one is the month when the quarter starts.
        
        self.quarter=1 ---> self.month_fiscal_year_starts
        self.quarter=2 ---> self.month_fiscal_year_starts + 3
        self.quarter=3 ---> self.month_fiscal_year_starts + 6
        self.quarter=4 ---> self.month_fiscal_year_starts + 9
        
        The second integer is either 0 or -1, depending on whether the quarter starts in calendar year
        self.fiscal_year or self.fiscal_year-1
        '''
        months_since_new_year = (self.month_fiscal_year_starts -1) + self.quarter*3 -2
        return (months_since_new_year-1) % 12+1, int((months_since_new_year-1)/12) -1
    
    def _ends_on_month(self):
        '''
        Helper method to compute the calendar month when the quarter ends. 
        Returns two integers. The first one is the month when the quarter ends:
        
        self.quarter=1 ---> self.month_fiscal_year_starts + 2
        self.quarter=2 ---> self.month_fiscal_year_starts + 5
        self.quarter=3 ---> self.month_fiscal_year_starts + 8
        self.quarter=4 ---> self.month_fiscal_year_starts + 11
        
        The second integer is either 0 or -1, depending on whether the quarter ends in calendar year
        self.fiscal_year or self.fiscal_year-1
        '''
        months_since_new_year = (self.month_fiscal_year_starts - 1) + self.quarter*3
        return (months_since_new_year -1) % 12 + 1, int((months_since_new_year-1)/12) -1