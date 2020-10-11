import os
import csv
import logging
import argparse
from decimal import Decimal
from inspect import stack

from dateutil import parser

from data_unifier.exceptions import DataDirDoesNotExistError


logger = logging.getLogger(__name__)
DEFAULT_LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class CSVReader:

    def __init__(self, data_path):
        if not os.path.isdir(data_path):
            raise DataDirDoesNotExistError('Data directory for does not exist')

        self.data_path = data_path
        self._csv_files = []

    @property
    def csv_files(self):
        if not self._csv_files:
            self._load_files()
        return self._csv_files

    def _load_files(self):
        for root, sub_dirs, file_names in os.walk(self.data_path):
            if not sub_dirs:
                for file_name in file_names:
                    file_path = os.path.join(root, file_name)
                    self._csv_files.append(CSVFile(file_path))


class CSVFile:

    DELIMITER = ','
    FIELDS_TO_HANDLER_MAPPING = {
        'timestamp': parser.parse,
        'date': parser.parse,
        'date_readable': parser.parse,
        'type': str,
        'transaction': str,
        'amount': Decimal,
        'amounts': Decimal,
        'euro': Decimal,
        'cents': Decimal,
        'from': int,
        'to': int}

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._headers = {}
        self._rows = ()

    @property
    def headers(self) -> dict:
        if not self._headers:
            self._load_data_from_file()
        return self._headers

    @property
    def rows(self) -> tuple:
        if not self._rows:
            self._load_data_from_file()
        return self._rows

    def _load_data_from_file(self):
        with open(self.file_path) as csv_file:
            csv_file = csv.reader(csv_file, delimiter=self.DELIMITER)
            self._headers = tuple(next(csv_file))
            self._rows = self._convert_rows_values_type(csv_file)

    def _convert_rows_values_type(self, rows):
        converted_rows = []
        for row in rows:
            converted_row = []
            for header, value in zip(self._headers, row):
                try:
                    field_type = self.FIELDS_TO_HANDLER_MAPPING[header]
                    converted_row.append(field_type(value))
                except (ValueError, TypeError):
                    logger.exception(f'value {value} for header {header} was not converted!')
                    converted_row.append(value)
            converted_rows.append(converted_row)
        return tuple(converted_rows)


class FieldProcessor:

    def __init__(self, csv_reader: CSVReader):
        self.fields_handlers = FieldsHandlers()
        self.csv_reader = csv_reader
        self.result_rows = ()
        self._raw_headers = self.fields_handlers.raw_headers

    def process_csv_files(self):
        logger.info('Start processing...')

        result_rows = [self.fields_handlers.headers]
        for csv_file in self.csv_reader.csv_files:
            result_rows.extend(self.process_csv_file(csv_file))
        self.result_rows = result_rows

        logger.info('Processing was finished')

    def process_csv_file(self, csv_file: CSVFile):
        csv_rows = []
        for row in csv_file.rows:
            csv_row = dict(zip(csv_file.headers, row))
            csv_row = self._process_row(csv_row)
            csv_rows.append([csv_row.get(header, '') for header in self._raw_headers])
        return csv_rows

    def _process_row(self, row: dict):
        result_row = {}
        for header_source in row:
            for handler in self.fields_handlers.get_handlers(header_source):
                result_row.update(handler(header_source, row))

        return result_row


class FieldsHandlers:

    ANY_FIELD_HANDLERS = ['_pass_field']

    QUANTIZE_VALUE = Decimal('0.01')
    ZERO_DECIMAL = Decimal('0')

    VALID_TRANSACTION_TYPES = ('add', 'remove')

    FIELDS_HANDLERS = {
        'timestamp': ['_reading_date'],
        'date': ['_reading_date'],
        'date_readable': ['_reading_date'],
        'type': ['_transaction_type'],
        'transaction': ['_transaction_type'],
        'amount': ['_amount', '_euro', '_cents'],
        'amounts': ['_amount', '_euro', '_cents'],
        'euro': ['_amount', '_euro'],
        'cents': ['_amount', '_cents'],
        'to': ANY_FIELD_HANDLERS,
        'from': ANY_FIELD_HANDLERS}

    def __init__(self):
        self._raw_headers = ()

    @property
    def raw_headers(self):
        if not self._raw_headers:
            headers = []
            for key, values in self.FIELDS_HANDLERS.items():
                if values == self.ANY_FIELD_HANDLERS:
                    headers.append(key)
                else:
                    for value in values:
                        if value not in headers:
                            headers.append(value)
            self._raw_headers = tuple(headers)

        return self._raw_headers

    @property
    def headers(self):
        return [self._raw_header_to_header(raw_header) for raw_header in self.raw_headers]

    def get_handlers(self, header_name):
        handlers = []
        for handler_name in self.FIELDS_HANDLERS.get(header_name, self.ANY_FIELD_HANDLERS):
            handlers.append(getattr(self, handler_name))
        return handlers

    def _raw_header_to_header(self, method_name):
        return method_name.strip('_').replace('_', ' ').capitalize()

    def _reading_date(self, header_source, row):
        try:
            return {stack()[0].function: row[header_source].isoformat()}
        except:
            logger.exception(
                f'value for `reading date` field was not processed,'
                f' expected type `datetime`')
            return {stack()[0].function: row[header_source]}

    def _transaction_type(self, header_source, row):
        try:
            value = row[header_source].lower()
            if value not in self.VALID_TRANSACTION_TYPES:
                logger.warning(
                    f'value {value} is not valid transaction type,'
                    f'expected types are {self.VALID_TRANSACTION_TYPES}')
            return {stack()[0].function: value}
        except:
            logger.exception(f'value for `transaction type` field was not processed')
            return {stack()[0].function: row[header_source]}

    def _amount(self, header_source, row):
        try:
            if header_source == 'euro':
                amount = row[header_source] + (row.get('cents', self.ZERO_DECIMAL) / 100)
            elif header_source == 'cents':
                amount = (row[header_source] / 100) + row.get('euro', self.ZERO_DECIMAL)
            else:
                amount = row[header_source]

            return {stack()[0].function: amount.quantize(self.QUANTIZE_VALUE)}
        except:
            logger.exception(f'value for `amount` field was not processed')
            return {stack()[0].function: row[header_source]}

    def _euro(self, header_source, row):
        try:
            return {stack()[0].function: Decimal(int(row[header_source]))}
        except:
            logger.exception(f'value for `euro` field was not processed')
            return {stack()[0].function: row[header_source]}

    def _cents(self, header_source, row):
        try:
            header_target = stack()[0].function
            if 'amount' in header_source:
                return {header_target: (row[header_source] % 1).quantize(self.QUANTIZE_VALUE)}
            return {header_target: Decimal(row[header_source])}

        except:
            logger.exception(f'value for `cents` field was not processed')
            return {stack()[0].function: row[header_source]}

    def _pass_field(self, header_source, row):
        return {header_source: row[header_source]}


class Writer:

    DELIMITER = ','

    def __init__(self, field_processor: FieldProcessor):
        self.field_processor = field_processor

    def save_data_to_csv_file(self, file_name='unified_file'):
        logger.info('Start writing...')
        with open(f'{file_name}.csv', 'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=self.DELIMITER)
            for row in self.field_processor.result_rows:
                csv_writer.writerow(row)
        logger.info('Writing was finished')


def main():
    logging.basicConfig(format=DEFAULT_LOGGING_FORMAT, level=logging.INFO)
    parser = argparse.ArgumentParser(description='Data-unifier',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('data_path', type=str, help='The path to the input data')
    arguments = parser.parse_args()

    csv_reader = CSVReader(data_path=arguments.data_path)
    field_processor = FieldProcessor(csv_reader)
    field_processor.process_csv_files()
    writer = Writer(field_processor)
    writer.save_data_to_csv_file()


if __name__ == '__main__':
    main()



