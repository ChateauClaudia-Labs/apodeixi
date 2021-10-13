import datetime                                 as _datetime
import calendar                                 as _calendar
import re                                       as _re

from apodeixi.util.a6i_error                    import ApodeixiError


class FY_Quarter():
    '''
    Represents a quarter in the fiscal year. The fiscal year runs from the 1st of the month initialized in the constructure. 
    Years are only supported from 2012 onwards.
    
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

        if month_fiscal_year_starts not in range(1, 13):
            raise ValueError("Invalid `month_fiscal_year_starts`: should be an integer between 1 and 12, but got "
                                + str(month_fiscal_year_starts) + " instead.")
        self.month_fiscal_year_starts   = month_fiscal_year_starts
        self.fiscal_year                = fiscal_year
        self.quarter                    = quarter

    def build_FY_Quarter(parent_trace, formatted_time_bucket_txt, month_fiscal_year_starts=1, default_quarter=4):
        '''
        Parses the string `formatted_time_bucket_txt`, and returns a FY_Quarter object constructed from that.

        If the parsing is not possible then it raises an Apodeixi error.

        The quarter portion might be optional, and spaces are allowed. Thus, all of the following are valid
        possible values for `formatted_time_bucket_txt`:
         
            "Q3 FY23", "Q3 FY 23", " Q3 FY 23 ", "FY23", "FY 25", "FY 2026", "Q 4 FY 29" 

        If the quarter is not provided, it is assumed to be Q4

        @param month_fiscal_year_starts An int between 1 and 12, corresponding to the month of the year
                        when the fiscal year starts. January is 1 and December is 12.
        @param default_quarter An int between 1 and 4. In situations where the quarter is not provided (e.g., 
                        `formatted_time_bucket_txt` is something like "FY 22"), then this is used as the default
                        value for the quarter in the result. Otherwise this parameter is ignored.
        '''
        REGEX           = "^\s*(Q\s*([1-4]))?\s*FY\s*(([0-9][0-9])?[0-9][0-9])\s*$"
        if type(formatted_time_bucket_txt) != str:
            raise ApodeixiError(parent_trace, "Invalid time bucket: expected a string, but instead was given a "
                                                + str(type(formatted_time_bucket_txt)))
        m               = _re.search(REGEX, formatted_time_bucket_txt)
        if m==None or len(m.groups())!= 4:
            raise ApodeixiError(parent_trace, "Invalid time bucket `" + formatted_time_bucket_txt + "`. Use a valid format, "
                                                + "such as 'Q2 FY23', 'Q1 FY 25', 'FY 26', or FY 1974")

        # If the input is "Q 4 FY 29", then [m.group(1), m.group(2), m.group(3), m.group(4)] is:
        #       
        #           ['Q 4', '4', '29', None]
        #
        if m.group(2) == None:
            if not default_quarter in [1, 2, 3, 4]:
                raise ApodeixiError(parent_trace, "Problem with parsing time bucket `" + formatted_time_bucket_txt + "`: "
                                                    + " the given default_quarter should be an integer between 1 and 4, not "
                                                    + str(default_quarter))
            quarter     = default_quarter
        else:
            quarter     = int(m.group(2))
        year            = int(m.group(3))
        if year < 100:
            year        += 2000     # For example, FY23 means the year is 2023, not 23
        
        return FY_Quarter(year, quarter, month_fiscal_year_starts=1)

    def less_than(self, parent_trace, other_quarter):
        '''
        Returns True or False, depending on whether self lies before the other_quarter (returns True), or
        not (return False).

        Raises an ApodeixiError if the `other_quarter` is not an FY_Quarter object.
        '''
        if type(other_quarter) != FY_Quarter:
            raise ApodeixiError(parent_trace, "Can only do `less_than` comparison against another FY_Quarter, but "
                                                "was give a '" + str(type(other_quarter)) + "' instead")

        my_last_day         = self.last_day()
        other_last_day      = other_quarter.last_day()

        if my_last_day < other_last_day:
            return True
        else:
            return False
        
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
    
    def display(self):
        return self.displayQuarter() + " " + self.displayFY()

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